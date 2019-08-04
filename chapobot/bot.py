from expiringdict import ExpiringDict
import praw
from praw.models import Redditor

import chapobot.model as model


class ChapoBot(object):

    def __init__(self):
        self.reddit = praw.Reddit(site_name="chapobot")
        self.db = model.Database()
        self._chapo_cache = ExpiringDict(max_len=10000, max_age_seconds=900)

    def _count_chapo_posts(self, user: Redditor) -> int:
        count = 0
        for submission in user.submissions.new(limit=200):
            if submission.subreddit.display_name == "ChapoTrapHouse":
                count += 1
        self._chapo_cache[user.name] = count
        return count

    def stream(self, subreddit: str) -> None:
        print(f"Beginning Chapo scan on {subreddit}")
        subreddit = self.reddit.subreddit(subreddit)
        for comment in subreddit.stream.comments():
            print(f'Processing comment {comment.id} from {comment.author.name}')
            chapo_posts = self._chapo_cache.get(comment.author.name)
            record_exists = self.db.identifier_exists(comment.id)
            if not record_exists:
                if chapo_posts is None:
                    chapo_posts = self._count_chapo_posts(comment.author)
                    is_chapo = chapo_posts > 10
                    if is_chapo:
                        print(f"{comment.author.name} failed purity test with {chapo_posts}/200 recent chapo posts")
                        warning_message = f"**Warning** it has been detected that this account may be a chapo poster. Out " \
                                          f"of {comment.author.name}'s last 200 posts, {chapo_posts} of them are chapo" \
                                          f" posts. "
                        # comment.reply(warning_message)
                self.db.insert_new_record(comment.id, comment.author.name, chapo_posts > 10)


if __name__ == "__main__":
    bot = ChapoBot()
    bot.stream('destiny')
