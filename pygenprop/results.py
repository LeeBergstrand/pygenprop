#!/usr/bin/env python

"""
Created by: Lee Bergstrand (2018)

Description: The genome property tree class.
"""

import json
import pandas as pd
from copy import deepcopy
from sqlalchemy.orm import sessionmaker
from pygenprop.tree import GenomePropertiesTree
from pygenprop.assign import assign_genome_property, AssignmentCache
from pygenprop.assignment_database import Base, Sample, PropertyAssignment, StepAssignment


class GenomePropertiesResults(object):
    """
    This class contains a representation of a table of results from one or more genome properties assignments.
    """

    def __init__(self, *genome_properties_results: AssignmentCache, genome_properties_tree: GenomePropertiesTree):
        """
        Constructs the genome properties results object.

        :param genome_properties_tree: The global genome properties tree.
        :param genome_properties_results_dict: One or more parsed genome properties assignments.
        """

        property_tables = []
        step_tables = []
        sample_names = []
        for assignment in genome_properties_results:
            sample_names.append(assignment.sample_name)
            property_table, step_table = create_assignment_tables(genome_properties_tree, assignment)
            property_tables.append(property_table)
            step_tables.append(step_table)

        combined_properties_table = pd.concat(property_tables, axis=1)
        combined_step_table = pd.concat(step_tables, axis=1)
        combined_properties_table.columns = sample_names
        combined_step_table.columns = sample_names

        self.tree = genome_properties_tree
        self.sample_names = sample_names
        self.property_results = combined_properties_table
        self.step_results = combined_step_table

    def get_property_result(self, genome_property_id, sample=None):
        """
        Gets the assignment results for a given genome property.

        :param sample:
        :param genome_property_id: The id of the genome property to get results for.
        :return: A list containing the assignment results for the genome property in question.
        """

        if sample:
            property_results = self.property_results[sample]
        else:
            property_results = self.property_results

        try:
            if sample:
                property_result = property_results.loc[genome_property_id]
            else:
                property_result = property_results.loc[genome_property_id].tolist()
        except KeyError:
            property_result = ['NO'] * len(property_results.columns)

        return property_result

    def get_step_result(self, genome_property_id, step_number, sample=None):
        """
        Gets the assignment results for a given step of a genome property.

        :param sample: The sample for which to grab results for.
        :param genome_property_id: The id of the genome property that the step belongs too.
        :param step_number: The step number of the step.
        :return: A list containing the assignment results for the step in question.
        """

        if sample:
            step_results = self.step_results[sample]
        else:
            step_results = self.step_results

        try:
            if sample:
                property_result = step_results.loc[genome_property_id].loc[step_number]
            else:
                property_result = step_results.loc[genome_property_id].loc[step_number].tolist()
        except KeyError:
            property_result = ['NO'] * len(step_results.columns)
        return property_result

    @property
    def properties(self):
        """
        Generates a list of properties for which there are assignments for.
        :return: A list of genome property identifiers.
        """
        return self.property_results.index.tolist()

    def get_step_numbers_for_property(self, genome_property_id):
        """
        Gets the numbers of the steps that support a property.
        :param genome_property_id: The id of the genome property for which we wants steps.
        :return: A list of step numbers.
        """
        return self.step_results.loc[genome_property_id].index.tolist()

    def to_json(self, file_handle=None):
        """
        Returns a JSON representation of the step results.
        :return: A nested dict of the assignment results and sample names.
        """
        json_data = {'sample_names': self.sample_names, 'property_tree': self.generate_json_tree(self.tree.root)}

        if file_handle:
            json.dump(json_data, file_handle)
        else:
            return json.dumps(json_data)

    def generate_json_tree(self, genome_properties_root):
        """
        Creates a tree based representation of the genome properties assignment results.

        :param genome_properties_root: The root element of the genome properties tree.
        :return: A nested dict of assignment results.
        """
        node_dict = {'property_id': genome_properties_root.id,
                     'name': genome_properties_root.name,
                     'enabled': False,
                     'result': self.get_property_result(genome_properties_root.id)}
        children = []
        for step in genome_properties_root.steps:
            step_child_properties = step.genome_properties

            if step_child_properties:
                for child in step_child_properties:
                    children.append(self.generate_json_tree(child))
            else:
                step_dict = {'step_id': step.number,
                             'name': step.name,
                             'enabled': False,
                             'result': self.get_step_result(genome_properties_root.id,
                                                            step.number)}
                children.append(step_dict)
        node_dict['children'] = children

        return node_dict

    def create_assignment_database(self, engine):
        """
        Write the assignments to a database.
        :param engine: An SQLAlchemy engine.
        """
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        current_session = sessionmaker(bind=engine)()

        for sample_name in self.sample_names:
            sample = Sample(name=sample_name)

            sample_step_assignments = []
            sample_property_assignments = []
            for property_identifier in self.properties:
                property_result = self.get_property_result(property_identifier,
                                                           sample=sample.name)

                property_assignment = PropertyAssignment(sample=sample)
                property_assignment.identifier = property_identifier
                property_assignment.assignment = property_result

                current_steps_assignments = []
                for step_number in self.get_step_numbers_for_property(property_identifier):
                    step_result = self.get_step_result(property_identifier, step_number, sample=sample.name)

                    if step_result == 'YES':
                        current_steps_assignments.append(StepAssignment(number=step_number,
                                                                        property_assignment=property_assignment))
                    else:
                        continue  # Skip steps which are not 'YES' to save space.

                property_assignment.step_assignments = current_steps_assignments
                sample_step_assignments.extend(current_steps_assignments)
                sample_property_assignments.append(property_assignment)

            current_session.add_all([sample, *sample_property_assignments, *sample_step_assignments])
            current_session.commit()
            current_session.close()


def create_assignment_tables(genome_properties_tree: GenomePropertiesTree, assignment_cache: AssignmentCache):
    """
    Takes a results dictionary from the long form parser and creates two tables. One for property results and
    one for step results. The longform results file has only leaf assignment results. We have to bootstrap the rest.

    :param genome_properties_tree: The global genome properties tree.
    :param assignment_cache: Per-sample genome properties results from the long form parser.
    :return: A tuple containing an property assignment table and step assignments table.
    """
    sanitized_assignment_cache = create_synchronized_assignment_cache(assignment_cache, genome_properties_tree)

    # Take known assignments and matched InterPro member database
    # identifiers and calculate assignments for all properties.
    assignments = bootstrap_assignments(sanitized_assignment_cache, genome_properties_tree)

    property_table = pd.DataFrame.from_dict(assignments.property_assignments,
                                            orient='index', columns=['Property_Result'])
    property_table.index.names = ['Genome_Property_ID']

    step_table = pd.DataFrame(create_step_table_rows(assignments.step_assignments),
                              columns=['Genome_Property_ID', 'Step_Number', 'Step_Result'])
    step_table.set_index(['Genome_Property_ID', 'Step_Number'], inplace=True)

    return property_table, step_table


def bootstrap_assignments(assignment_cache, genome_properties_tree):
    """
    Recursively fills in assignments for all genome properties in the genome properties tree based of existing cached
    assignments and InterPro member database identifiers.

    :param assignment_cache: A cache containing step and property assignments and InterPro member database matches.
    :param genome_properties_tree:
    :return:
    """
    # Bootstrap the other assignments from the leaf assignments.
    assign_genome_property(assignment_cache, genome_properties_tree.root)

    return assignment_cache


def create_synchronized_assignment_cache(assignment_cache, genome_properties_tree):
    """
    Remove genome properties from the assignment cache that are not found in both the genome properties tree and
    the assignment cache. This prevents situations where different versions of the cache and tree cannot find each
    others genome properties.

    :param assignment_cache: A cache containing step and property assignments and InterPro member database matches.
    :param genome_properties_tree: The global genome properties tree.
    :return: An assignment cache containing data for genome properties shared between the tree and cache.
    """
    tree_identifiers = set(genome_property.id for genome_property in genome_properties_tree)
    assignment_cache_identifiers = set(assignment_cache.genome_property_identifiers)

    unshared_identifiers = tree_identifiers.symmetric_difference(assignment_cache_identifiers)

    sanitized_assignment_cache = deepcopy(assignment_cache)

    for identifier in unshared_identifiers:
        sanitized_assignment_cache.flush_property_from_cache(identifier)

    return sanitized_assignment_cache


def create_step_table_rows(step_assignments):
    """
    Unfolds a step result dict of dict and yields a step table row.

    :param step_assignments: A dict of dicts containing step assignment information ({gp_key -> {stp_key --> result}})
    """
    for genome_property_id, step in step_assignments.items():
        for step_number, step_result in step.items():
            yield genome_property_id, step_number, step_result
