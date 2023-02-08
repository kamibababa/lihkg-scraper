if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--thread", required=True)
    parser.add_argument("-p", "--pages", required=False)
    parser.add_argument("-o", "--output-folder", required=False, default="./output")
    args = parser.parse_args()
    thread_id = args.thread
    page_numbers = args.pages
    output_folder_path = args.output_folder

    import copy
    from datetime import datetime, timezone
    import logging
    import sys

    import scrapers
    from dao import ImageDao, PageDao, ThreadDao
    from post_processing import consolidate_messages, download_images

    LOG_FORMAT = "%(asctime)s %(filename)s [%(levelname)s] %(message)s"
    logger = logging.getLogger("lihkg-scraper")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    page_numbers_actual = set()
    if page_numbers is not None:
        for page_range in page_numbers.split(","):
            for page in range(
                int(page_range.split("-")[0]),
                int(page_range.split("-")[-1]) + 1,
            ):
                page_numbers_actual.add(page)

    scrape_time_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    thread_dao = ThreadDao(output_folder_path, thread_id, scrape_time_str)
    image_dao = ImageDao(output_folder_path, thread_id, scrape_time_str)
    page_dao = PageDao(output_folder_path, thread_id, scrape_time_str)

    logger.info(
        f"Scraping {'page ' + ','.join(map(str, page_numbers_actual)) if len(page_numbers_actual) > 0 else 'all pages'} of thread {thread_id}. Output files will be saved in {thread_dao.thread_folder_path}"
    )

    if len(page_numbers_actual) == 0:
        pages = scrapers.scrape_thread(thread_id, open_new_tab=True)
    else:
        pages = scrapers.scrape_pages(
            thread_id,
            page_numbers=page_numbers_actual,
            open_new_tab=True,
        )

    for page_number, page_data in pages:
        page_dao.save_page(page_number, page_data)

    # Process thread data and write to topic.json
    thread_data = copy.deepcopy(page_data["response"])
    del thread_data["page"]
    del thread_data["item_data"]
    # if "me" in thread_data:
    #     del thread_data["me"]

    thread_dao.save_topic(thread_data)

    # Consolidate messages and write to messages.json
    consolidate_messages(page_dao, thread_dao)

    # Download images and save images and image mappings to images/ and images.json respectively
    download_images(thread_dao, image_dao)

    logger.info(
        f"Scraping completed. Data have been saved to {thread_dao.thread_folder_path}"
    )
