import argparse
import os
import re
import instaloader
import logging
import instagrapi

logger = logging.getLogger(__name__)

L = instaloader.Instaloader()

# L.login(USER, PASSWORD)  # (login)
# L.interactive_login(USER)  # (ask password on terminal)
# L.load_session_from_file(USER)  # (load session created w/
#  `instaloader -l USERNAME`)


def parse_url(url: str, loader: instaloader.Instaloader):
    url = url.strip()  # Remove leading/trailing whitespace
    post_shortcode = re.search(r"/p/(.*)/", url)
    if post_shortcode is not None:
        try:
            post = instaloader.Post.from_shortcode(L.context, post_shortcode[1])
            L.download_post(post, target=post_shortcode[1])
            logger.info(f"Downloaded successfully from {url}")
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

    if args.url:
        post_shortcode = re.search(r"/p/(.*)/?", args.url)
        if post_shortcode is not None:
            try:
                post = instaloader.Post.from_shortcode(
                    L.context, post_shortcode[1]
                )
                logger.info("Downloaded successfully.")
                L.download_post(post, target=post_shortcode[1])
            except Exception as e:
                logger.error(f"Error downloading from {args.url}: {e}")
                error_url.append(args.url)
                with open("error.txt", "a+") as error:
                    error.write(args.url + "\n")
    if args.input:
        with open(args.input, "r") as inpt, open("error.txt", "a+") as error:
            for url in inpt:
                parse_url(url=url, loader=L)

    # login required
    if client is None:
        exit(0)

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
