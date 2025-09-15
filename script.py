import argparse
import re
import instaloader
import logging

logger = logging.getLogger(__name__)

L = instaloader.Instaloader()

# L.login(USER, PASSWORD)  # (login)
# L.interactive_login(USER)  # (ask password on terminal)
# L.load_session_from_file(USER)  # (load session created w/
#  `instaloader -l USERNAME`)


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
        "--log_level",
        dest="log_level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "-c",
        "--cookies",
        help="Path to a JSON file containing cookies for authentication.",
    )
    args = parser.parse_args()
    logger.setLevel(args.log_level)

    error_url = []
    L.dirname_pattern = f"{args.output}/{{target}}"
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
    if args.input:
        with open(args.input, "r") as f:
            for url in f:
                url = url.strip()  # Remove leading/trailing whitespace
                post_shortcode = re.search(r"/p/(.*)/", url)
                if post_shortcode is not None:
                    try:
                        post = instaloader.Post.from_shortcode(
                            L.context, post_shortcode[1]
                        )
                        L.download_post(post, target=post_shortcode[1])
                        logger.info(f"Downloaded successfully from {url}")
                    except Exception as e:
                        logger.error(f"Error downloading from {url}: {e}")
                        error_url.append(url)
    with open("error.txt", "a+") as file:
        for i in error_url:
            file.write(i + "\n")
