
from antevents.base import Publisher
from antevents.internal import extensionmethod 
import antevents.linq.take

@extensionmethod(Publisher)
def first(this):
    """Take the first element of the stream. Sends out on_completed after
    forwarding the first element. If the stream is empty, we will just 
    pass on the completed notification we get from the incoming stream.
    """
    return this.take(1)
