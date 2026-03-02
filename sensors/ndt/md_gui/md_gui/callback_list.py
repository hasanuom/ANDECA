import collections
import types
from enum import Enum

class CallbackList:
    def __init__(self):
        self._callbacks = collections.defaultdict(list)

        # Debug print statements
        self._debug_print = False

    def register_callback(self, id, callback_method: callable):
        # if id is an Enum use the name string for the dict key
        if isinstance(id, Enum):
            id = id.name
        self._callbacks[id].append(callback_method)

    def call_callback(self, id, *args: tuple):

        if isinstance(id, Enum):
            id = id.name

        try:
            if self._debug_print:
                print("calling back")
                print(self._callbacks[id])
                print(self._callbacks[id][0])
                print(self._callbacks)
                print(args)
                print(*args)
            if len(args) == 0:  # No additional arguments
                self._callbacks[id][0]()
            else:

                if args[0] is None: # first additional argument is None
                    self._callbacks[id][0]()
                # elif isinstance(args[0], types.FunctionType): # first arg is a function
                #     # TODO: this section
                #     g = list(*args)
                #     x = g[0]()
                #     self._callbacks[id][0](x)
                else:
                    self._callbacks[id][0](*args)

        except KeyError:
            print("Callback not set")
            # Do nothing - callback has not been set
            pass
        except TypeError:
            print("Callback type error")
            pass
