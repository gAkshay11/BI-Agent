# memory.py
class SlidingWindowMemory:
    def __init__(self, max_turns: int = 6):
        self.max_turns = max_turns
        self.messages = []

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_turns:
            self.messages = self.messages[-self.max_turns:]

    def get(self) -> list:
        return self.messages

    def clear(self):
        self.messages = []

    def __len__(self):
        return len(self.messages)