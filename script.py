import argparse
import os
from os.path import basename
import re
import logging
import sys  # Added for sys.exit
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


# "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
USER_AGENT = "Instagram 410.0.0.0.96 Android (33/13; 480dpi; 1080x2400; xiaomi; M2007J20CG; surya; qcom; en_US; 641123490)"

# import debugpy
#
# debugpy.breakpoint()


# Helper function to download a single media item (photo or video)
def download_resource_item(
    client: instagrapi.Client,
    username: str,
    item: Union[Media, Resource],
    code: str,
    folder: str,
    error_file,
):
    """Downloads a single media item (photo or video) and its thumbnail."""
    # Determine the base filename. 'item' can be 'media' object or an item from 'media.resources'.
    filename_base = f"{username}-{code}-{item.pk}"
    try:
        if item.media_type == MediaType.PHOTO.value:
            client.photo_download_by_url(
                url=item.thumbnail_url, filename=filename_base, folder=folder
            )
        elif item.media_type == MediaType.VIDEO.value:
            # video thumbnail
            client.photo_download_by_url(
                url=item.thumbnail_url,
                filename=filename_base + "-thumb",
                folder=folder,
            )
            client.video_download_by_url(
                url=item.video_url, filename=filename_base, folder=folder
            )
        else:
            error_message = f'Media type "{item.media_type}" unknown for item {item.pk} (code={code})'
            logger.warning(error_message)
            error_file.write(
                f"Unsupported media: {error_message} in folder {folder}\n"
            )
            error_file.flush()
    except Exception as e:
        error_message = f"Error downloading item {item.pk} from {username} (code={code}): {e}"
        logger.error(error_message)
        error_file.write(
            f"Download Error: {error_message} for URL {item.url if hasattr(item, 'url') else 'N/A'}\n"
        )
        error_file.flush()


def download_thumbnail(
    media: Media,
    client: instagrapi.Client,
    filename: str,
    folder: str,
) -> str:
    if media.thumbnail_url is None:
        target = media.resources[0].thumbnail_url
    else:
        target = media.thumbnail_url
    path = client.photo_download_by_url(
        url=target,
        filename=filename,
        folder=folder,
    )
    return path


def media_unsave(
    client: instagrapi.Client,
    media: Media,
    collection_pk: str,
):
    try:
        collection_pk = int(collection_pk)
    except ValueError:
        # for All posts, collection_pk is a string
        collection_pk = None

    client.media_unsave(media_id=media.id, collection_pk=collection_pk)


def parse_story(url: str, client: instagrapi.Client, folder: str):
    pks = []
    try:
        pk = client.story_pk_from_url(url)
        pks.append(pk)
    except IndexError:
        url = url.lstrip("https://")
        url = url.rstrip("/")
        _, _, user = url.split("/")
        user = client.user_id_from_username(username=user)
        stories = client.user_stories(user_id=user)
        for s in stories:
            pks.append(s.pk)

    for pk in pks:
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
                    client=client,
                    username=media.user.username,
                    item=media,
                    code=code,
                    folder=target_folder,
                    error_file=error_file,
                )
                return
            elif media.media_type == MediaType.PHOTO.value:
                download_resource_item(
                    client=client,
                    username=media.user.username,
                    item=media,
                    code=code,
                    folder=target_folder,
                    error_file=error_file,
                )
                return
            elif media.resources:  # Album (check if resources exist)
                for resource in media.resources:
                    download_resource_item(
                        client=client,
                        username=media.user.username,
                        item=resource,
                        code=code,
                        folder=target_folder,
                        error_file=error_file,
                    )
            else:
                error_message = f"Unsupported media type ({media.media_type}) or no resources found for post {code} at {url}"
                logger.warning(error_message)
                error_file.write(f"Unsupported Media: {error_message}\n")
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
                error_message = f"{url}: Instaloader fallback failed with {ie}"
                logger.error(error_message)
                error_file.write(
                    f"Instaloader Fallback Error: {error_message}\n"
                )
                error_file.flush()
                return True

        except Exception as e:
            # Catch-all for other exceptions during instagrapi processing
            error_message = f"Error processing {url}: {e}"
            logger.error(error_message)
            error_file.write(f"General Error: {error_message}\n")
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
        help="The file name to store media links to be downloaded",
    )
    parser.add_argument(
        "--link_markdown",
        default=None,
        help="The markdown file name to download collection links and thumbnail to",
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


def download_collection_links(
    client: instagrapi.Client,
    collection_pk: str,
    folder: str,
    output_file: str,
    error_file,
    markdown: bool = False,
    unsave: bool = False,
):
    """
    Downloads media links from a collection and optionally writes them to a
    markdown file with thumbnails.
    """
    anonymous_client = instagrapi.Client()
    anonymous_client.set_user_agent(USER_AGENT)
    medias = client.collection_medias(collection_pk=collection_pk, amount=0)

    images_dir_name = "images"
    images_dir_path = Path(folder).joinpath(images_dir_name)
    os.makedirs(images_dir_path, exist_ok=True)
    output_file = Path(folder).joinpath(output_file)

    with open(output_file, "a+") as links_file:
        for m in medias:
            url = f"https://www.instagram.com/p/{m.code}/"
            logger.info(f"Processing link {url}")
            try:
                if markdown:
                    thumbnail_filename_base = (
                        f"{m.user.username}-{m.code}-{m.pk}"
                    )
                    thumbnail_path = download_thumbnail(
                        media=m,
                        client=anonymous_client,
                        filename=thumbnail_filename_base,
                        folder=images_dir_path,
                    )
                    # image link item uses relative path
                    thumbnail_path = Path(images_dir_name).joinpath(
                        Path(thumbnail_path).name
                    )
                    links_file.write(f"- [{m.title}]({url})\n")
                    links_file.write(f"  ![]({thumbnail_path})\n")
                    links_file.flush()
                else:
                    links_file.write(url + "\n")
                    links_file.flush()

                if unsave:
                    media_unsave(
                        client=client, media=m, collection_pk=collection_pk
                    )
            except Exception as e:
                error_message = f"Error processing markdown for {url}: {e}"
                logger.error(error_message)
                error_file.write(f"Markdown Error: {error_message}\n")
                error_file.flush()
                continue


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    logger.setLevel(args.log_level)

    # Configure instaloader patterns
    L.dirname_pattern = f"{args.output}"
    L.filename_pattern = "{profile}-{target}-{mediaid}"

    client = instagrapi.Client()
    client.set_user_agent(USER_AGENT)
    if args.login:
        try:
            client.login_by_sessionid(args.login)
        except Exception as e:  # Catch specific exception for better handling
            logger.warning(
                f"Login by sessionid failed: {e}. Trying interactive/manual login."
            )
            try:
                sessionid = input("sessionid:")
                client.login_by_sessionid(sessionid=sessionid)
            except Exception as e_session:
                logger.warning(
                    f"Login by sessionid (input) failed: {e_session}. Trying username/password."
                )
                try:
                    name = input("username:")
                    passwd = input("password:")
                    vcode = input("verification code:")
                    client.login(
                        username=name, password=passwd, verification_code=vcode
                    )
                except Exception as e_manual:
                    logger.error(f"Manual login failed: {e_manual}")
                    # Decide if you want to exit or proceed without login
                    # sys.exit(1) # Optionally exit if login is critical

        client.delay_range = [1, 3]

    collection_pk = None
    if args.collection:
        try:
            collection_pk = client.collection_pk_by_name(args.collection)
        except Exception as e:
            logger.error(f"Could not find collection '{args.collection}': {e}")
            sys.exit(1)  # Exit if collection is not found and required

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
            try:
                with open(args.input, "r") as inpt:
                    for url in inpt:
                        parse_url(
                            url=url.strip(),  # strip whitespace from URL
                            client=client,
                            folder=args.output,
                            error_file=error,
                        )
            except FileNotFoundError:
                logger.error(f"Input file not found: {args.input}")
                sys.exit(1)

        if args.download_links or args.link_markdown:
            if not args.collection or not collection_pk:
                logger.error(
                    "Collection name is required and must be valid for --download_links or --link_markdown."
                )
                sys.exit(1)

            # If --download_links is specified, write to that file.
            if args.download_links:
                download_collection_links(
                    client=client,
                    collection_pk=collection_pk,
                    folder=args.output,
                    output_file=args.download_links,
                    error_file=error,
                    unsave=args.unsave,
                )

            # If --link_markdown is specified, generate markdown with thumbnails.
            # This can be used in conjunction with --download_links or independently.
            if args.link_markdown:
                download_collection_links(
                    client=client,
                    collection_pk=collection_pk,
                    folder=args.output,
                    output_file=args.link_markdown,  # Use link_markdown for the output file name if specified
                    error_file=error,
                    markdown=True,  # Pass link_markdown for markdown generation
                    unsave=args.unsave,
                )

        if args.following:
            write_following(client=client)

        # interactive block
        url = lambda url: parse_url(
            url=url.strip(), client=client, folder=args.output, error_file=error
        )
        story = lambda url: parse_story(
            url=url.strip(), client=client, folder=args.output
        )
