import re
import sublime
import sublime_plugin
from datetime import datetime
from .logtime import logtime


class LogtimeFilterCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.query_from_input()

    def query_from_input(self):
        self.view.window().show_input_panel(
            'query', '',
            on_done=self.filter_and_sum,
            on_change=self.filter,
            on_cancel=self.unfold_all
        )

    def filter_and_sum(self, query):
        self.filter(query)
        content = self.view.substr(sublime.Region(0, self.view.size()))
        try:
            transactions = logtime.Log(content).filter(query)
        except:
            return
        self.show_sum(transactions)

    def filter(self, query):
        self.unfold_all()
        try:
            query = logtime.parse_query(query)
        except Exception as e:
            print(e)
            return
        content = self.view.substr(sublime.Region(0, self.view.size()))
        lines_to_fold = self.find_lines_to_fold(content, query)
        self.fold_lines(lines_to_fold)

    def find_lines_to_fold(self, content, query):
        not_to = set(self.find_lines_not_to_fold(content, query))
        for i in range(0, len(content.splitlines())):
            if i not in not_to:
                yield i

    def find_lines_not_to_fold(self, content, query):
        datetime_pattern = re.compile('\d\d\d\d-\d\d-\d\d \d\d:\d\d')
        lines = content.splitlines()
        start_date = None
        start_date_line = None
        end_date = None
        end_date_line = None
        tags = None
        tags_line = None
        for i, line in enumerate(lines):
            if not line:
                continue
            if datetime_pattern.match(line):
                date = datetime.strptime(line, '%Y-%m-%d %H:%M')
                if start_date:
                    end_date_line = i
                    end_date = date
                else:
                    start_date_line = i
                    start_date = date
            else:
                tags_line = i
                tags = line.split(' - ')
            if start_date and end_date and tags is not None:
                logitem = logtime.LogItem(start_date, end_date, tags)
                if query(logitem):
                    yield start_date_line
                    yield tags_line
                    yield end_date_line
            if start_date and end_date:
                start_date = end_date
                start_date_line = end_date_line
                end_date = None
        if start_date and tags:
            logitem = logtime.LogItem(start_date, datetime.now(), tags)
            if query(logitem):
                yield start_date_line
                yield tags_line

    def fold_lines(self, indices):
        regions_to_fold = self.find_regions_to_fold(indices)
        for region in self.coalesce_neighboring_regions(regions_to_fold):
            self.view.fold(region)

    def find_regions_to_fold(self, indices):
        for index in indices:
            yield self.view.line(self.view.text_point(index, 0))

    def coalesce_neighboring_regions(self, regions):
        prev_region = None
        for region in regions:
            if prev_region:
                if prev_region.b == region.a - 1:
                    prev_region = sublime.Region(prev_region.a, region.b)
                else:
                    yield prev_region
                    prev_region = region
            else:
                prev_region = region
            # yield region
        if prev_region: yield prev_region

    def unfold_all(self):
        self.view.unfold(sublime.Region(0, self.view.size()))

    def show_sum(self, transactions):
        total = transactions.sum()
        lines = [str(total)]
        self.view.window().show_quick_panel(
            lines, lambda _: None
        )
