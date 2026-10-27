from collections import deque

class LatencyPolicy:
    def __init__(self,now=0,underruns=0):
        self.last_count=underruns
        self.events=deque()
        self.last_underrun=now
        self.last_resize=now
    def update(self,total,current,requested,now):
        added=max(0,total-self.last_count)
        self.last_count=total
        while self.events and now-self.events[0]>10:
            self.events.popleft()
        if added:
            self.last_underrun=now
            self.events.extend([now]*min(added,3))
            if len(self.events)>=2:
                self.events.clear();self.last_resize=now
                return min(1024,current+64)
        elif current>requested and now-max(self.last_underrun,self.last_resize)>=60:
            self.last_resize=now
            return max(requested,current-64)
        return current
