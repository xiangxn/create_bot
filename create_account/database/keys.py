from mongoengine import *


class Keys(Document):
    meta = {"collection": "keys"}
    id = SequenceField(primary_key=True)
    address = StringField()
    privateKey = StringField()
    isTransfer = IntField(default=0)
    isMortgage = BooleanField(default=False)
