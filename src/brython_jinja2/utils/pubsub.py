"""
    The events module provides event dispatching services. The main class
    is the :class:`EventMixin` class which adds the :method:`bind` and
    :method:`emit` methods to the class. The :method:`bind` method registers event
    handlers for different events which are triggered by the :method:`emit`
    method.
"""
from ..platform.typing import List, Dict, Optional, Tuple, Iterable, Callable, Union, TypeVar, cast

class PubSubError(Exception):
    pass



ChannelT = str
PublisherT = TypeVar('PublisherT', bound='PublisherMixin')


class Message:
    """
        Message class encapsulating user data (:attribute:`data`)
        and message specific info (publishers, whether it was processed,
        message id...)
    """
    _lastid = 0

    def __init__(self, channel: ChannelT, publisher: PublisherT, data=None) -> None:
        self.publishers = [publisher] # type: List[PublisherT]
        self.channels = [channel]     # type: List[ChannelT]
        self.data = data
        self.processed = False
        self.messageid = Message._lastid
        Message._lastid += 1
        if Message._lastid > 2**31:
            Message._lastid = 0

    def republish(self, tgt: PublisherT) -> None:
        self.publishers.append(tgt)

    def add_channel(self, name: ChannelT) -> None:
        self.channels.append(name)

    @property
    def channel(self) -> ChannelT:
        return self.channels[-1]

    @property
    def publisher(self) -> PublisherT:
        return self.publishers[-1]

    def __repr__(self):
        # pylint: disable=line-too-long
        return "<Message "+repr(self.channels)+" target:"+repr(self.publishers)+"; data:"+repr(self.data)+">"


SubscriberT = Callable[[Message], None]


class PublisherMixin:
    """
        A Mixin class which adds methods to an object to make it possible
        for it to emit events and for others to bind to its emitted events
    """

    def __init__(self):
        self._subscribers = {}      # type: Dict[ChannelT, List[SubscriberT]]
        self._aggregating_from = [] # type: List[Tuple['PublisherMixin', SubscriberT, ChannelT]]

    def sub(self, channel: ChannelT, subscriber: Union[SubscriberT, PublisherT], forward_to: ChannelT = None) -> None:
        """
           Subscribes a subscriber to a channel.

           If :param:`subscriber` is an instance of `class`:PublisherMixin`, creates an artificial subscriber
           which forwards messages from the :param:`channel` channel to the :param:`forward_to` channel
           (or :param:`channel` if :param:`forward_to` is None) of the :param`:subscriber.
        """
        # pylint: disable=protected-access
        if  isinstance(subscriber, PublisherMixin):
            if forward_to is None:
                forward_to = channel
            generated_subscriber = generate_forwarding_subscriber(subscriber, forward_to)
            subscriber._aggregating_from.append((self, generated_subscriber, channel))
            subscriber = generated_subscriber

        if channel not in self._subscribers:
            self._subscribers[channel] = []

        self._subscribers[channel].append(cast(SubscriberT, subscriber))

    def stop_forwarding(self, restrict_to_channel: ChannelT = None, restrict_to_publisher: 'PublisherMixin' = None) -> None:
        """
        Stops forwarding messages which satisfy the following:

           1. If :param:`restrict_to_channel` is ``None`` the rule is satisfied. Otherwise the message
           satisfies the rule if it is in the :param:`restrict_to_channel` channel.

           2. If :param:`restrict_to_publisher` is ``None`` the rule is satisfied. Otherwise the message
           satisfies the rule if it was published by the :param:`restrict_to_publisher` publisher.
        """
        retain = []  # type: List[Tuple['PublisherMixin', SubscriberT, ChannelT]]
        for (publisher, subscriber, channel) in self._aggregating_from:
            if (restrict_to_channel is None or channel == restrict_to_channel) and (
                    restrict_to_publisher is None or publisher == restrict_to_publisher):
                publisher.unsub(channel, subscriber)
            else:
                retain.append((publisher, subscriber, channel))
        self._aggregating_from = retain

    def unsub(self, channel: ChannelT = None, subscriber: SubscriberT = None) -> None:
        """
        Unsubscribes subscribers.

           If :param:`channel` is None, unsubscribes ALL subscribers for all channels.

           If :param:`channel` is provided and not an PublisherMixin but :param:`subscriber` is None,
           unsubscribes all subscribers for the channel :param:`channel`.

           Otherwise unsubscribes only the specified @subscriber from the channel :param:`channel`.
        """
        if channel is None:
            self._subscribers = {}
            for (publisher, subscriber, channel) in self._aggregating_from:
                publisher.unsub(channel, subscriber)
            self._aggregating_from = []
        else:
            subscribers = self._subscribers.get(channel, [])
            if subscriber is None:
                subscribers.clear()
            else:
                subscribers.remove(subscriber)

    def pub(self, channel, message_data=None, _forwarded=False):
        """
            Publishes an message in the channel notifying (calling) all subscribers. Each
            subscriber will be passed an object of type :class:`Message` whose
            `data` attribute will contain :param:`message_data` and `publishers` and `names`
            attributes will be lists of publishers which published (or republished) the message
            and the channels on which the publishers sent it, starting from the first one and
            going up along the forwarding chain (if forward publishers were registered).

            NOTE: _forwarded should NOT be set by the users. It is used
            internally by forwarding publishers to indicate that this is a
            forwarded message.
        """
        if _forwarded and isinstance(message_data, Message):
            message_data.republish(self)
            message_data.add_channel(channel)
        else:
            message_data = Message(channel, self, message_data)
            subscribers = self._subscribers.get(channel, [])
            for subscriber in subscribers:
                subscriber(message_data)

def generate_forwarding_subscriber(publisher: PublisherMixin, forward_to_channel: str):
    def subscriber(message):
        publisher.pub(forward_to_channel, message, _forwarded=True)
    return subscriber

def add_publisher_mixin(obj):
    """Apply mixins to a class instance after creation"""
    # pylint: disable=protected-access
    base_cls = obj.__class__
    base_cls_name = obj.__class__.__name__
    obj.__class__ = type(base_cls_name, (PublisherMixin, base_cls), {})
    obj._subscribers = {}



def provides_channels(*args):
    def decorator(cls):
        if not issubclass(cls, PublisherMixin):
            raise PubSubError("Class "+str(cls)+" is not an PublisherMixin subclass, cannot publish messages!")
        cls.__channels = args
        return cls
    return decorator

