import argparse
import os
import re
import logging
from typing import Union
from enum import Enum
from pathlib import Path

import instaloader
import instagrapi
from instagrapi.types import Media, Resource

logger = logging.getLogger(__name__)

# instaloader for no login downloads
L = instaloader.Instaloader()

# L.login(USER, PASSWORD)  # (login)
# L.interactive_login(USER)  # (ask password on terminal)
# L.load_session_from_file(USER)  # (load session created w/
#  `instaloader -l USERNAME`)


class MediaType(Enum):
    PHOTO = 1
    VIDEO = 2


# Define custom exception for clarity
class AlbumNotDownload(Exception):
    """Custom exception for un-downloadable album media types."""

    pass


# Helper function to download a single media item (photo or video)
def download_resource_item(
    client: instagrapi.Client,
    item: Union[Media, Resource],
    code: str,
    folder: str,
    error_file,
):
    """Downloads a single media item (photo or video) and its thumbnail."""
    # Determine the base filename. 'item' can be 'media' object or an item from 'media.resources'.
    filename_base = f"{item.user.username}-{code}-{item.pk}"
    try:
        if item.media_type == MediaType.PHOTO.value:
            client.photo_download_by_url(
                item.thumbnail_url, filename_base, folder
            )
        elif item.media_type == MediaType.VIDEO.value:
            # video thumbnail
            client.photo_download_by_url(
                item.thumbnail_url, filename_base + "-thumb", folder
            )
            client.video_download_by_url(item.video_url, filename_base, folder)
        else:
            error_message = f'Media type "{item.media_type}" unknown for item {item.pk} (code={code})'
            logger.warning(error_message)
            error_file.write(
                f"Unsupported media: {error_message} in folder {folder}"
            )
            error_file.flush()
    except Exception as e:
        error_message = f"Error downloading item {item.pk} from {item.user.username} (code={code}): {e}"
        logger.error(error_message)
        error_file.write(
            f"Download Error: {error_message} for URL {item.url if hasattr(item, 'url') else 'N/A'}"
        )
        error_file.flush()


def parse_story(url: str, client: instagrapi.Client, folder: str):
    pk = client.story_pk_from_url(url)
    info = client.story_info(story_pk=pk)
    filename = f"{info.user.username}-{pk}"
    try:
        client.story_download(story_pk=pk, filename=filename, folder=folder)
    except Exception as e:
        logger.error(f"Error downloading from {url}: {e}")


def parse_url(
    url: str,
    client: instagrapi.Client,
    folder: str,
    error_file,
    sub_folder: bool = False,
) -> bool:
    """Parses a URL and downloads the corresponding Instagram media."""
    url = url.strip()
    code_match = re.search(r"/p/(.*)/", url)
    if code_match is not None:
        code = code_match[1]
        try:
            target_folder = folder
            if sub_folder:
                target_folder = str(Path(folder).joinpath(code))
                os.makedirs(name=target_folder, exist_ok=True)

            pk = client.media_pk_from_code(code=code)
            media = client.media_info(media_pk=pk)

            if media.media_type == MediaType.VIDEO.value:
                download_resource_item(
                    client, media, code, target_folder, error_file
                )
                return
            elif media.media_type == MediaType.PHOTO.value:
                download_resource_item(
                    client, media, code, target_folder, error_file
                )
                return
            elif media.resources:  # Album (check if resources exist)
                for resource in media.resources:
                    download_resource_item(
                        client, resource, code, target_folder, error_file
                    )
            else:
                error_message = f"Unsupported media type ({media.media_type}) or no resources found for post {code} at {url}"
                logger.warning(error_message)
                error_file.write(f"Unsupported Media: {error_message}")
                error_file.flush()
                return True

        except instagrapi.exceptions.LoginRequired:
            logger.warning(
                f"Login required for {url}, attempting download with Instaloader."
            )
            try:
                post = instaloader.Post.from_shortcode(
                    context=L.context, shortcode=code
                )
                L.download_post(post=post, target=code)
                logger.info(
                    f"Downloaded successfully (Instaloader fallback) from {url}"
                )
            except Exception as ie:
                error_message = f"Instaloader fallback failed for {url}: {ie}"
                logger.error(error_message)
                error_file.write(f"Instaloader Fallback Error: {error_message}")
                error_file.flush()
                return True

        except Exception as e:
            # Catch-all for other exceptions during instagrapi processing
            error_message = f"Error processing {url}: {e}"
            logger.error(error_message)
            error_file.write(f"General Error: {error_message}")
            error_file.flush()
            return True
        return False
    logger.error(f"not a post with url: {url}")
    return True


def create_parser():
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
        default=None,
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
        "--following",
        default=None,
        action="store_true",
        help="Download following account to following.txt",
    )
    parser.add_argument(
        "--log_level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser


def write_following(client: instagrapi.Client):
    user_id = client.user_id
    f = client.user_following(user_id=user_id, use_cache=False, amount=0)
    with open("following.txt", "w") as file:
        for k, v in f.items():
            file.write(f"{v.username}, {v.full_name}, {v.pk}\n")


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    logger.setLevel(args.log_level)

    # Configure instaloader patterns
    L.dirname_pattern = f"{args.output}"
    L.filename_pattern = f"{{profile}}-{{target}}-{{mediaid}}"

    client = instagrapi.Client()
    client.set_user_agent(
        "Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)"
        # "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    )
    if args.login:
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

    if args.collection:
        collection_pk = client.collection_pk_by_name(args.collection)

    with open("error.txt", "a+") as error:
        if args.url:
            parse_url(
                url=args.url,
                client=client,
                folder=args.output,
                error_file=error,
            )

        if args.story:
            parse_story(url=args.story, client=client, folder=args.output)

        if args.input:
            with open(args.input, "r") as inpt:
                for url in inpt:
                    parse_url(
                        url=url,
                        client=client,
                        folder=args.output,
                        error_file=error,
                    )

        if args.download_links:
            assert args.collection
            collection_pk = client.collection_pk_by_name(args.collection)
            medias = client.collection_medias(
                collection_pk=collection_pk, amount=0
            )
            with open(args.download_links, "a+") as links:
                for m in medias:
                    url = f"https://www.instagram.com/p/{m.code}/"
                    links.write(url)
                    if args.unsave:
                        try:
                            client.media_unsave(
                                media_id=m.id, collection_pk=collection_pk
                            )
                        except ValueError:
                            error.write(
                                f"Unsave failed for {url}"
                            )  # Log unsave error
                            error.flush()

        if args.following:
            write_following(client=client)

        # interactive block
        url = lambda url: parse_url(
            url=url, client=client, folder=args.output, error_file=error
        )
        story = lambda url: parse_story(
            url=url, client=client, folder=args.output
        )
