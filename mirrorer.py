import lzma
import os
import shutil
import tarfile
import time
from distutils.dir_util import copy_tree

import requests
from git import Repo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

XPATH = '//*[@id="main"]/div/div/div/table/tbody/tr'
SOURCE = "./vivaldi-source/"
TARGET = "./vivaldi/"
DOWNLOAD_FILE = "./download.tar.xz"


def download_version(version):
    file = requests.get(version, allow_redirects=True)
    open(DOWNLOAD_FILE, "wb").write(file.content)
    return DOWNLOAD_FILE


def extract_to_repo(download):
    with lzma.open(download) as f:
        with tarfile.open(fileobj=f) as tar:
            tar.extractall("./")
    shutil.move(TARGET + ".git", "./.git.tmp")
    shutil.rmtree(TARGET)
    shutil.move(SOURCE, TARGET)
    shutil.move("./.git.tmp", TARGET + ".git")
    os.remove(download)


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
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, XPATH)))
    entries = driver.find_elements(By.XPATH, XPATH)
    num_versions = len(entries)
    versions = []
    for i in range(2, num_versions + 1):
        versions.append(
            driver.find_element(By.XPATH, XPATH + "[" + str(i) + "]" + "/td[1]/a")
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
        repo = Repo(TARGET)
        repo.git.reset("--hard", "origin/master")
        repo.git.checkout("master")
        repo.git.pull()
        with open("PROCESSED_VERSIONS", "r+") as f:
            processed_versions = f.readlines()
            versions = vivaldi_versions()
            unprocessed_versions = [
                k for k in versions.keys() if k not in processed_versions
            ]

            for version in sorted(
                unprocessed_versions, key=lambda v: list(map(int, v.split(".")))
            ):
                download = download_version(versions[version])
                extract_to_repo(download)
                commit(version)
                f.write(version + "\n")
        time.sleep(3600)


if __name__ == "__main__":
    main()
