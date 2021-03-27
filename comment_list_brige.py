class Comment:
  def __init__(self, tweet):
    self.author = Author(tweet.account.display_name)
    self.body = tweet.content
    if (len(self.body) == 0):
        self.body = '...'
    self.score = 0

class Author:
    def __init__(self, name):
        self.name = name
