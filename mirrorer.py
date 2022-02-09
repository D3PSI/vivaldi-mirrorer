import lzma
import os
import tarfile

import requests
from git import Repo
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

XPATH = '//*[@id="main"]/div/div/div/table/tbody/tr'


def download_version(version):
    file = requests.get(version, allow_redirects=True)
    open("./vivaldi/download.tar.xz", "wb").write(file.content)
    return "./vivaldi/download.tar.xz"


def extract_to_repo(download):
    with lzma.open(download) as f:
        with tarfile.open(fileobj=f) as tar:
            content = tar.extractall("./vivaldi/")
            allfiles = os.listdir("./vivaldi/vivaldi-source/")
            for f in allfiles:
                os.replace("./vivaldi/vivaldi-source/" + f, "./vivaldi/" + f)
    os.remove(download)


def commit(version):
    repo = Repo("./vivaldi/")
    files = repo.git.diff(None, name_only=True)
    for f in files.split("\n"):
        repo.git.add(f)
    repo.git.commit("-m", "[Version] {}".format(version))


def vivaldi_versions():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)
    driver.get("https://vivaldi.com/source/")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, XPATH)))
    entries = driver.find_elements_by_xpath(XPATH)
    num_versions = len(entries)
    versions = []
    for i in range(2, num_versions - 1):
        versions.append(
            driver.find_element_by_xpath(XPATH + "[" + str(i) + "]" + "/td[1]/a")
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
    # TODO Pull before doing anything else
    with open("PROCESSED_VERSIONS", "r+") as f:
        processed_versions = f.readlines()
        versions = vivaldi_versions()
        unprocessed_versions = [
            (k, v) for (k, v) in versions.items() if k not in processed_versions
        ]
        for (version, elem) in unprocessed_versions:
            download = download_version(elem)
            extract_to_repo(download)
            commit(version)
            f.write(version + "\n")


if __name__ == "__main__":
    main()
