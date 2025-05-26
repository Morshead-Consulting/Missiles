class Message:
    def __init__(self, sender_id, data, timestamp, corruption=False):
        self.sender_id = sender_id
        self.data = data
        self.timestamp = timestamp
        self.corruption = corruption
