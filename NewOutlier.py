import tweepy
import yaml
from twilio.rest import TwilioRestClient
from datetime import datetime

def getAllLinks(consumer_key, consumer_secret):
    auth = tweepy.AppAuthHandler(consumer_key, consumer_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True,
               wait_on_rate_limit_notify=True)
     
    if (not api):
        print ("Can't Authenticate")
        sys.exit(-1)

    maxTweets = 10000000    # Some arbitrary large number
    tweetsPerQry = 100      # this is the max the API permits
    sinceId = None
    max_id = -1L
    tweetCount = 0
    howFresh = 2            # days
    allLinks = set()
    restockLinks = set()

    print("Downloading max {0} tweets".format(maxTweets))
    
    while tweetCount < maxTweets:
        try:
            if (max_id <= 0):
                if (not sinceId):
                    new_tweets = api.user_timeline(screen_name='outlier', count=tweetsPerQry)
                else:
                    new_tweets = api.user_timeline(screen_name='outlier', count=tweetsPerQry,
                                            since_id=sinceId)
            else:
                if (not sinceId):
                    new_tweets = api.user_timeline(screen_name='outlier', count=tweetsPerQry,
                                            max_id=str(max_id - 1))
                else:
                    new_tweets = api.user_timeline(screen_name='outlier', count=tweetsPerQry,
                                            max_id=str(max_id - 1),
                                            since_id=sinceId)
            if not new_tweets:
                print("No more tweets found")
                break
            for tweet in new_tweets:
                if 'urls' in tweet.entities:
                    for url in tweet.entities['urls']:
                        # only add to file if it's a product link
                        if 'shop.outlier' in url['expanded_url'].lower():
                            allLinks.add(str(url['expanded_url']))                            
                            # restocks in the last two days
                            if ('restock' in tweet.text.lower() or 'stock' in tweet.text.lower()) and abs(datetime.now() - tweet.created_at).days < howFresh:
                                restockLinks.add(str(url['expanded_url']))
    
            tweetCount += len(new_tweets)
            print("Downloaded {0} tweets".format(tweetCount))
            max_id = new_tweets[-1].id
        except tweepy.TweepError as e:
            # Just exit if any error
            print("some error : " + str(e))
            break

    print ("Downloaded {0} tweets".format(tweetCount))

    return allLinks, restockLinks


if __name__=='__main__':

    with open("config.yaml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    #twitter deets 
    consumer_key = cfg['twitter']['consumer_key']
    consumer_secret = cfg['twitter']['consumer_secret']
    access_token = cfg['twitter']['access_token']
    access_secret = cfg['twitter']['access_secret']

    #twilio deets
    accountSID = cfg['twilio']['accountSID']
    authToken = cfg['twilio']['authToken']

    myTwilioNumber = cfg['twilio']['myTwilioNumber']
    myCellNumber = cfg['twilio']['myCellNumber']

    twilioCli = TwilioRestClient(accountSID, authToken)

    storedLinks = set(line.strip() for line in open('tweets.txt')) #links available at last run
    allLinks, restockLinks = getAllLinks(consumer_key, consumer_secret)
    newLinks = allLinks.difference(storedLinks)
    
    fName = 'tweets.txt' # We'll store the tweets in a text file.

    # write links to file
    with open(fName, 'w') as f:
        for link in allLinks:
            f.write(link + '\n')

    # new things to buy
    if newLinks:
        print('ready your wallet')
        message = twilioCli.messages.create(body='new product(s)' + ', '.join(newLinks), from_=myTwilioNumber, to=myCellNumber)

    if restockLinks:
        print('wallet on standby')
        message = twilioCli.messages.create(body='restock(s)' + ', '.join(newLinks), from_=myTwilioNumber, to=myCellNumber)


