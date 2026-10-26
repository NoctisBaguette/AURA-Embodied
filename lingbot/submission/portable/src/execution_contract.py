"""Finite request accounting shared by native simulator and portable service."""
import math


def request_budget(step_limit, prefix):
    if type(step_limit) is not int or not 1 <= step_limit <= 10000:
        raise ValueError('Invalid official action limit')
    if type(prefix) is not int or prefix not in (10, 50):
        raise ValueError('Unsupported execution prefix')
    return math.ceil(step_limit / prefix)


class Requests:
    def __init__(self):
        self.episodes = {}

    def validate(self, episode, chunk, seed, step_limit, prefix, actions_started):
        if not isinstance(episode, str) or not 1 <= len(episode) <= 100 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in episode):
            raise ValueError('Invalid episode identity')
        budget = request_budget(step_limit, prefix)
        if type(chunk) is not int or not 1 <= chunk <= budget:
            raise ValueError('Request exceeds finite episode budget')
        if type(seed) is not int or seed != 777 + chunk - 1:
            raise ValueError('Noise schedule differs')
        if type(actions_started) is not int or actions_started != (chunk - 1) * prefix or actions_started >= step_limit:
            raise ValueError('Request/action progress mismatch')
        previous = self.episodes.get(episode)
        if previous is None:
            if chunk != 1:
                raise ValueError('First request must be chunk one')
        elif previous != (chunk - 1, step_limit, prefix):
            raise ValueError('Duplicate, skipped request or changed execution contract')
        return min(prefix, step_limit - actions_started)

    def commit(self, episode, chunk, step_limit, prefix):
        self.episodes[episode] = (chunk, step_limit, prefix)
