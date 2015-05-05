# -*- coding: utf-8 -*-
"""Script used to post tweets as @NewHorizonsBot on Twitter."""
try:
    from urllib.request import urlopen, urlretrieve
except ImportError:  # Darn Python 2
    from urllib import urlopen, urlretrieve
import re
from twython import Twython
from astropy import log
from astropy.time import Time


def get_latest_images():
    """Returns a dictionary detailing the images most recently released.

    The web page distributing raw images from New Horizons uses javascript
    arrays to produce a gallery page, so we need to read in the contents of
    those arrays using regular expressions.
    """
    # First retrieve the page distributing the images
    webpage = urlopen('http://pluto.jhuapl.edu/soc/Pluto-Encounter/index.php')
    html = webpage.read()
    # Names of the javascript arrays are used to construct the web gallery:
    array_names = ['jpegArr', 'UTCArr', 'DescArr',
                   'TargetArr', 'RangeArr', 'ExpArr']
    images = {}
    for name in array_names:
        images[name] = re.findall(name+r".push\(\"([^\"]+)\"\)", str(html))
    return images


def generate_tweet(jpeg, utc, desc, target, myrange, exp):
    """Generates a @NewHorizonsBot tweet.

    Returns
    -------
    (status, image_fn): (str, str)
        Status message and filename of the image to upload.
    """
    # First create the URL to link to
    url = ('http://pluto.jhuapl.edu/soc/Pluto-Encounter/view_obs.php?'
           'image={}&utc_time={}&description={}&target={}&range={}&exposure={}'
           .format(jpeg, utc, desc, target, myrange, exp))
    url = url.replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
    # Then create a pretty status message
    time_object = Time(utc.replace('<br>', ' ')[0:19])
    pretty_time = time_object.datetime.strftime('%d %b %Y, %H:%M:%S UTC')
    status = ('#NewHorizons released a new image!\n'
              '⌚ {}.\n'
              '📍 {} from #Pluto.\n'
              '🔗 {}\n'.format(pretty_time.lstrip("0"), myrange, url))
    # Finally, make sure the image we are tweeting is on disk
    jpeg_prefix = 'http://pluto.jhuapl.edu/soc/Pluto-Encounter/'
    image_fn = '/tmp/newhorizonsbot.jpg'
    log.info('Downloading {}'.format(jpeg_prefix + jpeg))
    urlretrieve(jpeg_prefix + jpeg, image_fn)
    return (status, image_fn)


def post_tweet(status, media_fn):
    """Post media and an associated status message to Twitter."""
    import secrets
    twitter = Twython(secrets.APP_KEY, secrets.APP_SECRET,
                      secrets.OAUTH_TOKEN, secrets.OAUTH_TOKEN_SECRET)
    upload_response = twitter.upload_media(media=open(media_fn, 'rb'))
    response = twitter.update_status(status=status,
                                     media_ids=upload_response['media_id'])
    log.info(response)
    return twitter, response


if __name__ == '__main__':
    # Try to find an image that has not already been tweeted
    # Which images have already been tweeted?
    try:
        IMAGES_TWEETED = [line.strip() for line in
                          open('images-tweeted.txt').readlines()]
    except FileNotFoundError:
        log.warning('images-tweeted.txt not found')
        IMAGES_TWEETED = []

    images = get_latest_images()
    # Go back-to-forth to tweet the oldest non-tweeted image first
    for idx in range(len(images['jpegArr'])-1, -1, -1):
        archive_filename = images['jpegArr'][idx]
        if archive_filename not in IMAGES_TWEETED:
            status, image_fn = generate_tweet(jpeg=images['jpegArr'][idx],
                                              utc=images['UTCArr'][idx],
                                              desc=images['DescArr'][idx],
                                              target=images['TargetArr'][idx],
                                              myrange=images['RangeArr'][idx],
                                              exp=images['ExpArr'][idx])
            log.info(status)
            twitter, response = post_tweet(status, image_fn)
            # Remember that we tweeted this image
            history = open('images-tweeted.txt', 'a')
            history.write(archive_filename+'\n')
            history.close()
            # We're done
            break
