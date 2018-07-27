#!/usr/bin/env python

"""
Created by: Lee Bergstrand (2017)

Description: A simple unittest for testing the literature reference module.
"""

import unittest

from modules.genome_properties_longform_file_parser import parse_genome_property_longform_file


class TestParseLongform(unittest.TestCase):
    """A unit testing class for testing the literature_reference.py module. To be called by nosetests."""

    def test_parse_longform(self):
        simulated_property_file = """ PROPERTY: GenProp0001
                    Chorismate biosynthesis via shikimate
                    .	STEP NUMBER: 1
                    .	STEP NAME: Phospho-2-dehydro-3-deoxyheptonate aldolase
                    .	.	required
                    .	STEP RESULT: yes
                    .	STEP NUMBER: 2
                    .	STEP NAME: 3-dehydroquinate synthase
                    .	.	required
                    .	STEP RESULT: yes
                    RESULT: YES
                    PROPERTY: GenProp0053
                    Type II secretion
                    .	STEP NUMBER: 1
                    .	STEP NAME: Type II secretion system protein C
                    .	STEP RESULT: yes
                    .	STEP NUMBER: 10
                    .	STEP NAME: Type II secretion system protein L
                    .	.	required
                    .	STEP RESULT: yes
                    .	STEP NUMBER: 12
                    .	STEP NAME: Type II secretion system protein N
                    .	STEP RESULT: no
                    RESULT: PARTIAL
                    PROPERTY: GenProp0046
                    IPP biosynthesis
                    .	STEP NUMBER: 1
                    .	STEP NAME: IPP biosynthesis
                    .	.	required
                    .	STEP RESULT: no
                    RESULT: NO
                """

        rows = list(row.strip() for row in simulated_property_file.splitlines())

        properties = parse_genome_property_longform_file(rows)

        self.assertEqual(len(properties.keys()), 2)
        self.assertNotIn('GenProp0046', properties.keys())
        self.assertEqual(properties['GenProp0001']['step_results'], [1, 2])
        self.assertEqual(properties['GenProp0001']['partial'], False)
        self.assertEqual(properties['GenProp0053']['step_results'], [1, 10])
        self.assertEqual(properties['GenProp0053']['partial'], True)