# PurityBot

A simple reddit bot that tags users who post in "impure" subreddits.

Made for the memes to be had in /r/destiny

## Capabilities

The bot currently supports two modes

1. Automatic tagging of all "impure" comments
2. Purity test on request for posts/comments with configurable command

## Configuration

The bot relies on two ini files in the current working directory
to function.

* praw.ini : contains the reddit api configuration for praw
* puritybot.ini : contains all the purity bot specific configurations


## puritybot.ini

This is the main configuration file for the bot.  It supports the
following configuration keys.

| Key | Description | Default
---|---|---
HarassmentCooldownSeconds | The number of seconds to wait between tagging comments made by the same user | 900
PostLookbackPeriod|The number of posts to look back|200|
PurityThreshold|The number of impure posts to tolerate before the user fails the purity test|3
ImpureSubDisplayName|The comma seperate list of "impure" subreddits|ChapoTrapHouse,The_Donald,Hasan_Piker
SubredditToScan|The subreddit to scan|destiny
OnlyOnCommand|Only do purity tests on request|true
BotCommand|The bot purity test command|!puritytest

## Docker

The bot includes a simple Dockerfile that packages things up into a
runnable environment.  You should make sure that you configure your
praw.ini file before building the image.