"""
This module provides hotstrings capability using Xlib.

It is based on:
https://github.com/cryzed/bin/blob/master/hotstrings
"""

import collections

import Xlib
import Xlib.X
import Xlib.XK
import Xlib.display
import Xlib.ext.record
import Xlib.protocol

EXIT_FAILURE = 1
RECORD_CONTEXT_ARGUMENTS = (
    0,
    (Xlib.ext.record.AllClients,),
    ({
        'core_requests': (0, 0),
        'core_replies': (0, 0),
        'ext_requests': (0, 0, 0, 0),
        'ext_replies': (0, 0, 0, 0),
        'delivered_events': (0, 0),
        'device_events': (Xlib.X.KeyPress, Xlib.X.KeyRelease),
        'errors': (0, 0),
        'client_started': False,
        'client_died': False
    },)
)

# Load xkb to access XK_ISO_Level3_Shift
Xlib.XK.load_keysym_group('xkb')
event_field = Xlib.protocol.rq.EventField(None)


def parse_event_fields(data, display):
    while data:
        event, data = event_field.parse_binary_value(data, display, None, None)
        yield event


class RecordHandler:
    MODIFIER_KEY_MASKS = {
        'Shift': Xlib.X.ShiftMask,
        'Lock': Xlib.X.LockMask,
        'Control': Xlib.X.ControlMask,
        'Alt': Xlib.X.Mod1Mask,
        'Mod1': Xlib.X.Mod1Mask,
        'Mod2': Xlib.X.Mod2Mask,
        'Mod3': Xlib.X.Mod3Mask,
        'Mod4': Xlib.X.Mod4Mask,
        'Mod5': Xlib.X.Mod5Mask
    }

    def __init__(self, conn, record_conn, callback):
        self.conn = conn
        self.record_conn = record_conn
        self.callback = callback

        # Support for XK_ISO_Level3_Shift/AltGr:
        self.alt_gr_pressed = False
        self.alt_gr_keycodes = set(i[0] for i in self.conn.keysym_to_keycodes(Xlib.XK.XK_ISO_Level3_Shift))

    def get_modifier_state_index(self, state):
        # None = 0, Shift = 1, Alt = 2, Alt + Shift = 3,
        # AltGr = 4, AltGr + Shift = 5
        pressed = {n: (state & m) == m for n,
                   m in self.MODIFIER_KEY_MASKS.items()}
        index = 0
        if pressed['Shift']:
            index += 1
        if pressed['Alt']:
            index += 2
        if self.alt_gr_pressed:
            index += 4

        return index

    def key_pressed(self, event):
        # Manually keep track of AltGr state because it is not encoded in the
        # event.state byte
        if event.detail in self.alt_gr_keycodes:
            self.alt_gr_pressed = True

        keysym = self.conn.keycode_to_keysym(
            event.detail, self.get_modifier_state_index(event.state))
        character = self.conn.lookup_string(keysym)
        if character:
            self.callback(character)

    def key_released(self, event):
        if event.detail in self.alt_gr_keycodes:
            self.alt_gr_pressed = False

    def __call__(self, reply):
        # Ignore all replies that can't be parsed by parse_event_fields
        if not reply.category == Xlib.ext.record.FromServer:
            return

        for event in parse_event_fields(reply.data, self.record_conn.display):
            if event.type == Xlib.X.KeyPress:
                self.key_pressed(event)
            else:
                self.key_released(event)


class HotstringProcessor:
    BACKSPACE_CHARACTER = '\x08'

    def __init__(self, hotstrings, conn):
        self.hotstrings = hotstrings
        self.conn = conn
        self.root_window = self.conn.screen().root

        # Only keep at maximum the amount of characters of the
        # longest hotstring in the HotstringProcessor queue
        self.queue_size = max(len(k) for k in hotstrings.keys())
        self.queue = collections.deque(maxlen=self.queue_size)

        # These stay the same for all requests, so just keep a local copy
        self._default_key_press_event_arguments = dict(
            time=Xlib.X.CurrentTime, root=self.root_window, child=Xlib.X.NONE,
            root_x=0, root_y=0, event_x=0, event_y=0, same_screen=1
        )
        self._default_key_release_event_arguments = self._default_key_press_event_arguments

    def make_key_press_event(self, detail, state, window, **kwargs):
        arguments = self._default_key_press_event_arguments.copy()
        arguments.update(kwargs)
        return Xlib.protocol.event.KeyPress(detail=detail, state=state, window=window, **arguments)

    def make_key_release_event(self, detail, state, window, **kwargs):
        arguments = self._default_key_release_event_arguments.copy()
        arguments.update(kwargs)
        return Xlib.protocol.event.KeyRelease(detail=detail, state=state, window=window, **arguments)

    # TODO: Figure out a way to find keycodes not assigned in
    # the current keyboard mapping
    def string_to_keycodes(self, string_):
        for character in string_:
            code_point = ord(character)

            # TODO: Take a look at other projects using python-xlib to improve this
            # See Xlib.XK.keysym_to_string
            keycodes = tuple(self.conn.keysym_to_keycodes(code_point) or
                             self.conn.keysym_to_keycodes(0xFF00 | code_point))
            keycode = keycodes[0] if keycodes else None

            # TODO: Remap missing characters to available keycodes
            if not keycode:
                # verbose('No keycode found for: %r.' % character, file=sys.stderr)
                continue

            yield keycode

    def type_keycode(self, keycode, window):
        detail, state = keycode
        window.send_event(self.make_key_press_event(detail, state, window))
        window.send_event(self.make_key_release_event(detail, state, window))

    def type_keycodes(self, keycodes, window):
        for keycode in keycodes:
            self.type_keycode(keycode, window)

        self.conn.flush()

    def __call__(self, character):
        if character == self.BACKSPACE_CHARACTER and self.queue:
            self.queue.pop()
        else:
            self.queue.append(character)

        queue_string = ''.join(self.queue)
        backspace = tuple(self.string_to_keycodes(self.BACKSPACE_CHARACTER))
        window = self.conn.get_input_focus().focus

        for hotstring, action in self.hotstrings.items():
            if not queue_string.endswith(hotstring):
                continue

            if isinstance(action, str):
                replacement = action
            elif callable(action):
                replacement = action()
            else:
                # TODO: Raise?
                continue

            # Linefeeds don't seem to be sent by Xlib
            # so replace them with carriage returns: normalize \r\n to \r first
            # then replace all remaining \n with \r
            replacement = replacement.replace('\r\n', '\r').replace('\n', '\r')
            self.type_keycodes(backspace * len(hotstring), window)
            self.type_keycodes(self.string_to_keycodes(replacement), window)
            self.queue.clear()


def get_Xctx():
    conn = Xlib.display.Display()
    record_conn = Xlib.display.Display()
    record_ctx = record_conn.record_create_context(*RECORD_CONTEXT_ARGUMENTS)

    return (conn, record_conn, record_ctx)


def cleanup(conn, record_conn, record_ctx):
    record_conn.record_free_context(record_ctx)
    record_conn.close()
    conn.close()


def watch(hotstrings, conn, record_conn, record_ctx):
    """
    Start watching for hotstrings.

    hotstrings is a dictionary whose keys are strings and values are the callbacks.
    """

    if not hotstrings:
        return

    if not record_conn.has_extension('RECORD'):
        raise RuntimeError('X Record Extension Library not found.\n')

    hotstring_processor = HotstringProcessor(hotstrings, conn)

    record_handler = RecordHandler(conn, record_conn, hotstring_processor)
    record_conn.record_enable_context(record_ctx, record_handler)
