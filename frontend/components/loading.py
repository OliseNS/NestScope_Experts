"""
Loading animation components
"""

import time
import threading
import itertools
from streamlit.runtime.scriptrunner import add_script_run_ctx


class LoadingCarousel:
    """
    Context manager to display a carousel of loading messages.
    """

    def __init__(self, placeholder, messages):
        self.placeholder = placeholder
        self.messages = messages
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._animate)
        add_script_run_ctx(self.thread)

    def _animate(self):
        for message in itertools.cycle(self.messages):
            if self.stop_event.is_set():
                break
            self.placeholder.markdown(f"🔄 **{message}**")
            time.sleep(1.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        self.thread.join()
        self.placeholder.empty()
