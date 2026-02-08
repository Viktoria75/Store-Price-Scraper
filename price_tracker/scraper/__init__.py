"""Scraper package for Price Tracker."""

from price_tracker.scraper.base import BaseScraper
from price_tracker.scraper.http_scraper import HttpScraper
from price_tracker.scraper.selenium_scraper import SeleniumScraper

__all__ = ["BaseScraper", "HttpScraper", "SeleniumScraper"]
