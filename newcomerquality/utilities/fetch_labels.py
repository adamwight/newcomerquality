"""
Extracts 'damaging' and 'goodfaith' labels from campaign on a Wikilabels
server.  Assumes the general schema of the Edit quality campaign.

Usage:
    fetch_labels <campaign-url>
                 [--filter=<condition>...]
                 [--output=<path>]
                 [--debug]
                 [--verbose]

Options:
    <campaign-url>        The base URL of a campaign from which to extract
                          labels.
    --filter=<condition>  A condition for inclusion of labels in the output.
    --output=<path>       Path to an file to write output to
                          [default: <stdout>]
    --debug               Print debug logging
    --verbose             Print dots and stuff representing progress
"""
import json
import logging
import re
import sys
from collections import defaultdict
from statistics import mean

import docopt
import requests

from . import util


def main(argv=None):
    args = docopt.docopt(__doc__, argv=argv)

    logging.basicConfig(
        level=logging.DEBUG if args['--debug'] else logging.INFO,
        format='%(asctime)s %(levelname)s:%(name)s -- %(message)s',
        filename='logs/fetch.log', filemode='w',
    )
    logg = logging.getLogger()
    campaign_url = args['<campaign-url>']

    filter = Filter.from_strings(args['--filter'])

    if args['--output'] == "<stdout>":
        labels_f = sys.stdout
    else:
        labels_f = open(args['--output'], "w")

    verbose = args['--verbose']

    run(campaign_url, labels_f, filter, verbose, logg)


def run(campaign_url, labels_f, filter, verbose, logg):

    campaign_doc = requests.get(campaign_url, params={'tasks': ""}).json()

    completed = [t for t in campaign_doc['tasks'] if t['labels']]
    logg.info('Completed tasks found: {0}'.format(len(completed)))
    completed_row_oriented = [{'task_id': c['id'],
                               'user_id': c['data']['user_id'],
                               'rev_ids': c['data']['rev_ids'],
                               'damaging_label': c['labels'][0]['data']['damaging'],
                               'goodfaith_label': c['labels'][0]['data']['goodfaith'], } for c in completed]

    json.dump(completed_row_oriented,labels_f)

    # for task_doc in campaign_doc['tasks']:
    #     if not filter.filter(task_doc):
    #         if verbose:
    #             sys.stderr.write("s")
    #             sys.stderr.flush()
    #         continue
    #
    #     label_doc = aggregate_labels(task_doc['labels'])
    #     if label_doc is None:
    #         if verbose:
    #             sys.stderr.write(".")
    #             sys.stderr.flush()
    #     else:
    #         revision = task_doc['data']
    #         from IPython import embed; embed()
    #         revision.update(label_doc)
    #         labels_f.write(json.dumps(util.normalize_revision(revision)))
    #         labels_f.write("\n")


def aggregate_labels(label_docs):

    if len(label_docs) == 0:
        return None
    else:
        label_lists = defaultdict(list)
        if sum('automated' not in l['data'] for l in label_docs) > 0:
            relevant_label_docs = (l for l in label_docs
                                   if 'automated' not in l['data'])
            auto_labeled = False
        else:
            relevant_label_docs = (l for l in label_docs
                                   if 'automated' in l['data'])
            auto_labeled = True

        for l in relevant_label_docs:
            if l['data']['damaging'] is not None:
                label_lists['damaging'].append(l['data']['damaging'])
            if l['data']['goodfaith'] is not None:
                label_lists['goodfaith'].append(l['data']['goodfaith'])

        out = {'auto_labeled': auto_labeled}
        if 'damaging' in label_lists:
            out['damaging'] = mean(label_lists['damaging']) > 0.5
        if 'goodfaith' in label_lists:
            out['goodfaith'] = mean(label_lists['goodfaith']) >= 0.5

        return out


OPERATORS = {"=": lambda field, value: field == value,
             "!=": lambda field, value: field != value,
             ">": lambda field, value: field > value,
             ">=": lambda field, value: field >= value,
             "<": lambda field, value: field < value,
             "<=": lambda field, value: field <= value}
FILTER_RE = re.compile(r"([^.<>!=]+(\.[^.<>!=]+)*)" +
                       r"\s*(=|!=|>|>=|<|<=)\s*" +
                       r"(.+)", re.I)


class Filter:

    def __init__(self, conditions):
        self.conditions = conditions

    def filter(self, doc):
        return sum(condition(doc) for condition in self.conditions) == \
            len(self.conditions)

    @classmethod
    def from_strings(cls, condition_strings):
        conditions = []
        for condition_string in condition_strings:
            fields_string, _, operator, value_string = \
                FILTER_RE.match(condition_string).groups()

            conditions.append(
                lambda doc: OPERATORS[operator](query_json(fields_string, doc),
                                                json.loads(value_string)))

        return cls(conditions)


def query_json(field_string, doc):
    fields = field_string.split(".")
    return _query_json_fields(fields, doc)


def _query_json_fields(fields, doc):
    field = fields.pop(0)
    if len(fields) > 0:
        return _query_json_fields(fields, doc[field])
    else:
        return doc[field]
