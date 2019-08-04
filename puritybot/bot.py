import configparser
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Union

from expiringdict import ExpiringDict
import praw
from praw.models import Redditor, Comment, Submission

import puritybot.model as model


class PurityBot(object):

    def __init__(self,
                 harassment_cooldown: int,
                 post_lookback: int,
                 purity_threshold: int,
                 impure_subs: List[str],
                 bot_command: str) -> None:
        """
        Create a new instance of the PurityBot
        :param harassment_cooldown: the minimum threshold within which the bot will reply to the same users comments
        :param post_lookback: the number of posts to include in the lookback period when making a bias determination
        :param purity_threshold: the number of impure posts allowed before making a bias determination
        :param impure_subs: the list of impure subreddits
        :param bot_command: the command that triggers the bot if running in command only mode
        """
        self._reddit = praw.Reddit(site_name="PurityBot")
        self._db = model.Database("PurityBot")
        self._purity_cache = ExpiringDict(max_len=10000, max_age_seconds=harassment_cooldown)
        self._purity_threshold = purity_threshold
        self._impure_subs = impure_subs
        self._post_lookback = post_lookback
        self._bot_command = bot_command

    def _count_impure_posts(self, user: Redditor) -> Dict[str, int]:
        """
        Count the number of impure posts for a given user and store it in the purity cache
        :param user: the user to make a determination on
        :return: the impurity dict
        """
        counts = defaultdict(int)
        for submission in user.submissions.new(limit=self._post_lookback):
            if submission.subreddit.display_name in self._impure_subs:
                counts[submission.subreddit.display_name] += 1
        self._purity_cache[user.name] = counts
        return counts

    def stream(self, subreddit: str, only_on_command: bool) -> None:
        """
        Main run method for the bot, listens to a stream of posts coming from the given subreddit.  Replies to users
        whose bias passes the impurity threshold.
        :param subreddit: the subreddit to scan
        :param only_on_command: whether or not to only respond to comments when asked to via !puritytest
        """
        print(f"Beginning purity scan on {subreddit}")
        subreddit = self._reddit.subreddit(subreddit)
        for comment in subreddit.stream.comments():
            if only_on_command and self._bot_command in comment.body:
                if comment.is_root:
                    self.process_entry(comment.submission, force_reply=True)
                else:
                    self.process_entry(self._reddit.comment(id=comment.parent_id), force_reply=True)
            else:
                self.process_entry(comment, force_reply=False)

    def process_entry(self, entry: Union[Comment, Submission], force_reply: bool) -> None:
        """
        Process either a comment o
        :param entry: the entry to process
        :param force_reply: whether or not the bot should reply no matter what the result is
        """
        print(f'Processing comment {entry.id} from {entry.author.name}')
        num_impure_posts = self._purity_cache.get(entry.author.name)
        record_exists = self._db.identifier_exists(entry.id)
        if not record_exists:
            if num_impure_posts is None or force_reply:
                num_impure_posts = self._count_impure_posts(entry.author)
                sub_name, bias = determine_bias(num_impure_posts)
                is_impure = bias > self._purity_threshold
                if is_impure:
                    print(f"{entry.author.name} failed purity test with {bias}/{self._post_lookback} recent {sub_name} posts")
                    entry.reply(f"**Warning** it has been detected that this account may be a {sub_name} poster. Out of {entry.author.name}'s last {self._post_lookback} posts, {bias} of them are on {sub_name}\n\n***\n\nBot source available [here](https://github.com/derDeidra/PurityBot)")
                elif force_reply:
                    entry.reply('User has passed the purity test, they are to be trusted.\n\nBot source available [here](https://github.com/derDeidra/PurityBot)')
            else:
                sub_name, bias = determine_bias(num_impure_posts)
            self._db.insert_new_record(entry.id, entry.author.name, bias > self._purity_threshold)


def determine_bias(purity_dict: Dict[str, int]) -> Tuple[str, int]:
    """
    Attempts to determine which impure tag has the most bias
    :param purity_dict: the purity dict
    :return: a tuple containing the name of the biased subreddit and the degree of bias
    """
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
    """
    Determines the magnitude of a given integer
    :param x: the integer
    :return: the magnitude
    """
    return int(math.log10(x))


if __name__ == "__main__":
    cfg_parser = configparser.ConfigParser()
    cfg_parser.read('puritybot.ini')
    purity_bot_cfg = cfg_parser['PurityBot']
    bot = PurityBot(
        harassment_cooldown=int(purity_bot_cfg['HarassmentCooldownSeconds']),
        post_lookback=int(purity_bot_cfg['PostLookbackPeriod']),
        purity_threshold=int(purity_bot_cfg['PurityThreshold']),
        impure_subs=purity_bot_cfg['ImpureSubDisplayName'].split(','),
        bot_command=purity_bot_cfg['BotCommand']
    )
    bot.stream(purity_bot_cfg['SubredditToScan'], purity_bot_cfg.getboolean('OnlyOnCommand'))
