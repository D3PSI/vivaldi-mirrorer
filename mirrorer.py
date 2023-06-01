import logging
import logging.handlers
import lzma
import os
import shutil
import tarfile
import time

import requests
from git import Repo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

XPATH = '//*[@id="main"]/div/div/div/table/tbody/tr'
SOURCE = "./vivaldi-source/"
TARGET = "../vivaldi/"

smtp_handler = logging.handlers.SMTPHandler(
    mailhost=(os.environ["HOST"], int(os.environ["PORT"])),
    fromaddr=os.environ["FROM"],
    toaddrs=os.environ["TO"],
    subject="Vivaldi Bot ran into an exception",
    credentials=(os.environ["USER"], os.environ["PASS"]),
    secure=(),
)


logger = logging.getLogger()
logger.addHandler(smtp_handler)


def download_file(url):
    local_filename = url.split("/")[-1]
    with requests.get(url, stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename


def download_version(version):
    return download_file(version)


def extract_to_repo(download):
    with lzma.open(download) as f:
        with tarfile.open(fileobj=f) as tar:
            tar.extractall("./")
    os.remove(download)
    shutil.move(TARGET + ".git", "./.git.tmp")
    shutil.rmtree(TARGET)
    shutil.move(SOURCE, TARGET)
    if os.path.exists(TARGET + ".git"):
        if os.path.isdir(TARGET + ".git"):
            shutil.rmtree(TARGET + ".git")
        else:
            os.remove(TARGET + ".git")
    for root, dirs, files in os.walk(TARGET):
        for name in files:
            if name == ".git":
                if os.path.isdir(os.path.join(root, name)):
                    shutil.rmtree(os.path.join(root, name))
                else:
                    os.remove(os.path.join(root, name))
    shutil.move("./.git.tmp", TARGET + ".git")


def commit(version):
    repo = Repo(TARGET)
    repo.git.add(all=True)
    repo.git.commit("-m", "[Version] {}".format(version))
    repo.git.push()


def vivaldi_versions():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    driver.get("https://vivaldi.com/source/")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, XPATH)))
    entries = driver.find_elements(By.XPATH, XPATH)
    num_versions = len(entries)
    versions = []
    for i in range(2, num_versions + 1):
        versions.append(
            driver.find_element(
                By.XPATH, XPATH + "[" + str(i) + "]" + "/td[1]/a")
        )
    versions_dict = {}
    for version in versions:
        link = version.get_attribute("href")
        text_parts = version.text.split("_")
        text_split = text_parts[1].split(".")
        text = ".".join(text_split[:3])
        versions_dict[text] = link
    return versions_dict


def main():
    while True:
        try:
            repo = Repo(TARGET)
            repo.git.reset("--hard", "origin/master")
            repo.git.checkout("master")
            repo.git.pull()
            with open("PROCESSED_VERSIONS", "r+") as f:
                processed_versions = f.read().splitlines()
                versions = vivaldi_versions()
                unprocessed_versions = [
                    k for k in versions.keys() if k not in processed_versions
                ]

                for version in sorted(
                    unprocessed_versions, key=lambda v: list(
                        map(int, v.split(".")))
                ):
                    download = download_version(versions[version])
                    extract_to_repo(download)
                    commit(version)
                    f.writelines([version + "\n"])
                    f.flush()
            repo = Repo()
            repo.git.add("PROCESSED_VERSIONS")
            repo.git.commit(
                "-m", "[Version] Update PROCESSED_VERSIONS for {}".format(version))
            repo.git.push()
            time.sleep(3600)
        except KeyboardInterrupt:
            exit(0)
        except Exception as e:
            logger.exception(e)
            time.sleep(60 * 15)


if __name__ == "__main__":
    main()
