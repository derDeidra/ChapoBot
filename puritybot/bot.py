import configparser
import math
from collections import defaultdict
from typing import List, Dict, Tuple

from expiringdict import ExpiringDict
import praw
from praw.models import Redditor

import puritybot.model as model


class PurityBot(object):

    def __init__(self, harassment_cooldown: int, post_lookback: int, purity_threshold: int,
                 impure_subs: List[str]) -> None:
        self._reddit = praw.Reddit(site_name="PurityBot")
        self._db = model.Database()
        self._purity_cache = ExpiringDict(max_len=10000, max_age_seconds=harassment_cooldown)
        self._purity_threshold = purity_threshold
        self._impure_subs = impure_subs
        self._post_lookback = post_lookback

    def _count_impure_posts(self, user: Redditor) -> Dict[str, int]:
        counts = defaultdict(int)
        for submission in user.submissions.new(limit=self._post_lookback):
            if submission.subreddit.display_name in self._impure_subs:
                counts[submission.subreddit.display_name] += 1
        self._purity_cache[user.name] = counts
        return counts

    def stream(self, subreddit: str) -> None:
        print(f"Beginning Chapo scan on {subreddit}")
        subreddit = self._reddit.subreddit(subreddit)
        for comment in subreddit.stream.comments():
            print(f'Processing comment {comment.id} from {comment.author.name}')
            num_impure_posts = self._purity_cache.get(comment.author.name)
            record_exists = self._db.identifier_exists(comment.id)
            if not record_exists:
                if num_impure_posts is None:
                    num_impure_posts = self._count_impure_posts(comment.author)
                    sub_name, bias = determine_bias(num_impure_posts)
                    is_impure = bias > self._purity_threshold
                    if is_impure:
                        print(
                            f"{comment.author.name} failed purity test with {num_impure_posts}/{self._post_lookback} recent {sub_name} posts")
                        warning_message = f"**Warning** it has been detected that this account may be a {sub_name} poster. Out " \
                                          f"of {comment.author.name}'s last {self._post_lookback} posts, {bias} of them are on {sub_name}" \
                                          f" posts. "
                        # comment.reply(warning_message)
                else:
                    sub_name, bias = determine_bias(num_impure_posts)
                self._db.insert_new_record(comment.id, comment.author.name, bias > self._purity_threshold)


def determine_bias(purity_dict: Dict[str, int]) -> Tuple[str, int]:
    len_purity_dict = len(purity_dict)
    if len_purity_dict == 0:
        return '', 0
    elif len_purity_dict == 1:
        k = list(purity_dict.keys())[0]
        return k, purity_dict[k]
    else:
        sorted_items = sorted(purity_dict.items(), key=lambda k_v: k_v[1], reverse=True)
        mag_item_1 = determine_magnitude(sorted_items[0][1])
        mag_item_2 = determine_magnitude(sorted_items[1][1])
        if mag_item_1 > mag_item_2:
            return sorted_items[0]
        elif mag_item_1 < mag_item_2:
            return sorted_items[1]
        else:
            if sorted_items[0][1] > sorted_items[1][1]:
                return sorted_items[0]
            else:
                return sorted_items[1]


def determine_magnitude(x: int) -> int:
    return int(math.log10(x))


if __name__ == "__main__":
    cfg_parser = configparser.ConfigParser()
    cfg_parser.read('puritybot.ini')
    purity_bot_cfg = cfg_parser['PurityBot']
    bot = PurityBot(
        harassment_cooldown=int(purity_bot_cfg['HarassmentCooldownSeconds']),
        post_lookback=int(purity_bot_cfg['PostLookbackPeriod']),
        purity_threshold=int(purity_bot_cfg['PurityThreshold']),
        impure_subs=purity_bot_cfg['ImpureSubDisplayName'].split(',')
    )
    bot.stream('destiny')
