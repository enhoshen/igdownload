import argparse
import os
import re
from instagrapi.types import Media
import instaloader
import logging
import instagrapi
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

L = instaloader.Instaloader()

# L.login(USER, PASSWORD)  # (login)
# L.interactive_login(USER)  # (ask password on terminal)
# L.load_session_from_file(USER)  # (load session created w/
#  `instaloader -l USERNAME`)


class MediaType(Enum):
    PHOTO = 1
    VIDEO = 2


def parse_story(url: str, client: instagrapi.Client, folder: str):
    pk = client.story_pk_from_url(url)
    info = client.story_info(story_pk=pk)
    filename = f"{info.user.username}-{pk}"
    try:
        client.story_download(story_pk=pk, filename=filename, folder=folder)
    except Exception as e:
        logger.error(f"Error downloading from {url}: {e}")


def parse_url(url: str, client: instagrapi.Client, folder: str):
    url = url.strip()  # Remove leading/trailing whitespace
    code_match = re.search(r"/p/(.*)/", url)
    if code_match is not None:
        try:
            # post = instaloader.Post.from_shortcode(L.context, post_shortcode[1])
            # L.download_post(post, target=post_shortcode[1])
            # logger.info(f"Downloaded successfully from {url}")
            code = code_match[1]
            folder = str(Path(folder).joinpath(code))
            os.mkdir(path=folder)
            pk = client.media_pk_from_code(code=code)
            media = client.media_info(media_pk=pk)
            filename = f"{media.user.username}-{code}-{media.pk}"
            if media.media_type == MediaType.VIDEO.value:
                client.video_download_by_url(media.video_url, filename, folder)
                return
            if media.media_type == MediaType.PHOTO.value:
                client.photo_download_by_url(
                    media.thumbnail_url, filename, folder
                )
                return
            for resource in media.resources:
                filename = f"{media.user.username}-{code}-{resource.pk}"
                if resource.media_type == MediaType.PHOTO.value:
                    client.photo_download_by_url(
                        resource.thumbnail_url, filename, folder
                    )
                elif resource.media_type == MediaType.VIDEO.value:
                    client.video_download_by_url(
                        resource.video_url, filename, folder
                    )
                else:
                    raise AlbumNotDownload(
                        'Media type "{resource.media_type}" unknown for album (resource={resource.pk})'
                    )

        except Exception as e:
            logger.error(f"Error downloading from {url}: {e}")
            error_url.append(url)
            error.write(url + "\n")
            error.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Instagram images/videos."
    )
    parser.add_argument(
        "--url",
        help="The Instagram URL to download from.",
    )
    parser.add_argument(
        "-s",
        "--story",
        help="Story link",
    )
    parser.add_argument(
        "-i",
        "--input",
        help="input file with each line being a instagram url",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="downloads",
        help="The directory to save the media to.",
    )
    parser.add_argument(
        "-l",
        "--login",
        help="Account login, followed by session id",
    )
    parser.add_argument(
        "-c",
        "--collection",
        default="download",
        help="The collection to download links",
    )
    parser.add_argument(
        "--unsave",
        action="store_true",
        help="After operation done, unsave the media",
    )
    # collection operations
    parser.add_argument(
        "--download_links",
        default=None,
        help="Download media links to a file",
    )
    parser.add_argument(
        "--log_level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    args = parser.parse_args()
    logger.setLevel(args.log_level)

    error_url = []
    L.dirname_pattern = f"{args.output}/{{target}}"
    L.filename_pattern = f"{{target}}-{{date_utc}}"

    client = None
    if args.login:
        client = instagrapi.Client()
        client.set_user_agent(
            "Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)"
        )
        try:
            client.login_by_sessionid(args.login)
        except:
            try:
                sessionid = input("sessionid:")
                client.login_by_sessionid(sessionid=sessionid)
            except:
                name = input("username:")
                passwd = input("password:")
                vcode = input("verification code:")
                client.login(
                    username=name, password=passwd, verification_code=vcode
                )
        client.delay_range = [1, 3]

    # login required
    if client is None:
        exit(0)

    if args.url:
        parse_url(url=args.url, client=client, folder=args.output)

    if args.story:
        parse_story(url=args.story, client=client, folder=args.output)

    if args.input:
        with open(args.input, "r") as inpt, open("error.txt", "a+") as error:
            for url in inpt:
                parse_url(url=url, client=client, folder=args.output)

    if args.collection:
        collection_pk = client.collection_pk_by_name(args.collection)

    if args.download_links:
        collection_pk = client.collection_pk_by_name(args.collection)
        medias = client.collection_medias(collection_pk=collection_pk, amount=0)
        with open(args.download_links, "a+") as links, open(
            "error.txt", "a+"
        ) as error:
            for m in medias:
                url = f"https://www.instagram.com/p/{m.code}/\n"
                links.write(url)
                if args.unsave:
                    try:
                        client.media_unsave(
                            media_id=m.id, collection_pk=collection_pk
                        )
                    except ValueError:
                        error.write(url)
