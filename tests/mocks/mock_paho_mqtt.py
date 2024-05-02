class MockAsyncIterator:
    def __init__(self, seq):
        self.iter = iter(seq)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


class MockMQTTMessage:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload
