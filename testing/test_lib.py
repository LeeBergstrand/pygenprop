#!/usr/bin/env python

"""
Created by: Lee Bergstrand (2017)

Description: A simple unittest for testing functions from the lib module.
"""

import unittest
from modules.lib import create_marker_and_content, collapse_step_evidence_and_gene_ontologys, \
    collapse_genome_property_record, parse_genome_property_file
from modules.step import parse_steps
from modules.genome_property import parse_genome_property


class TestLib(unittest.TestCase):
    """A unit test class for lib functions which clean and parse genome properties files."""

    def test_create_marker_and_content(self):
        """Test that we can split genome property rows by marker and content."""
        genome_property_row = 'RL  EMBO J. 2001;20:6561-6569.'
        marker, content = create_marker_and_content(genome_property_row)

        self.assertEqual(marker, 'RL')
        self.assertEqual(content, 'EMBO J. 2001;20:6561-6569.')

    def test_collapse_step_evidence_and_gene_ontologys(self):
        """Test that we can clean up evidences and GO ids."""
        step = [
            ('--', ''),
            ('SN', '1'),
            ('ID', 'Aferr subtype specific proteins'),
            ('DN', 'Crispy Proteins'),
            ('RQ', '1'),
            ('EV', 'IPR017545; TIGR03114; TIGR03111;'),
            ('TG', 'GO:0043571;GO:0043579;'),
            ('EV', 'IPR017546; TIGR03114; TIGR03112;'),
            ('TG', 'GO:0043577;GO:0043579;')
        ]

        collapsed = collapse_step_evidence_and_gene_ontologys(step)
        parsed_step = parse_steps(collapsed)[0]

        expected_evidences = {'IPR017545', 'TIGR03114', 'TIGR03111', 'IPR017546', 'TIGR03112'}
        expected_gene_ontologies = {'GO:0043571', 'GO:0043579', 'GO:0043577'}

        self.assertEqual(parsed_step.evidence, expected_evidences)
        self.assertEqual(parsed_step.gene_ontology_ids, expected_gene_ontologies)

    def test_collapse_genome_property_record(self):
        """Test that we can clean up the overall genome property file."""
        property_rows = [
            ('AC', 'GenProp0002'),
            ('DE', 'Coenzyme F420 utilization'),
            ('TP', 'GUILD'),
            ('AU', 'Haft DH'),
            ('TH', '0'),
            ('RN', '[1]'),
            ('RM', '11726492'),
            ('RT', 'Structures of F420H2:NADP+ oxidoreductase with and without its'),
            ('RT', 'janky structure!'),
            ('RT', 'I surprised that worked!'),
            ('RA', 'Warkentin E, Mamat B, Sordel-Klippert M, Wicke M, Thauer RK, Iwata M,'),
            ('RL', 'EMBO J. 2001;20:6561-6569.'),
            ('DC', 'Methane Biosynthesis'),
            ('DR', 'IUBMB; misc; methane;'),
            ('CC', 'Coenzyme F420 (a 7,8-didemethyl-8-hydroxy 5-deazaflavin)'),
            ('CC', 'is a very important enzyme!'),
            ('**', 'Yo_Dog_its_Yolo'),
            ('**', 'a new film by the cool dudes!'),
            ('--', ''),
            ('SN', '1'),
            ('ID', 'LLM-family F420-associated subfamilies'),
            ('RQ', '0'),
            ('EV', 'IPR019910; TIGR03564; sufficient;'),
            ('--', ''),
            ('SN', '2'),
            ('ID', 'Methylene-5,6,7,8-tetrahydromethanopterin dehydrogenase'),
            ('RQ', '0'),
            ('EV', 'IPR002844; PF01993; sufficient;'),
            ('--', ''),
            ('SN', '3'),
            ('ID', 'PPOX-class probable F420-dependent enzyme'),
            ('RQ', '0'),
            ('EV', 'IPR019920; TIGR03618; sufficient;')
        ]

        clean_genome_property_record = collapse_genome_property_record(property_rows)

        first_genome_property = parse_genome_property(clean_genome_property_record)
        first_reference = first_genome_property.references[0]

        self.assertEqual(first_genome_property.description, 'Coenzyme F420 (a 7,8-didemethyl-8-hydroxy 5-deazaflavin) '
                                                            'is a very important enzyme!')
        self.assertEqual(first_genome_property.private_notes, 'Yo_Dog_its_Yolo a new film by the cool dudes!')
        self.assertEqual(first_reference.title, 'Structures of F420H2:NADP+ oxidoreductase with and without its janky '
                                                'structure! I surprised that worked!')

    def test_parse_genome_property_file(self):
        """Test if a physical genome properties file can be parsed."""
        genome_property_flat_file_path = './testing/test_constants/test_genome_properties.txt'

        with open(genome_property_flat_file_path) as genome_property_file:
            properties = parse_genome_property_file(genome_property_file)

        self.assertEqual(len(properties), 4)
