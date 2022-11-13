import numpy as np
import dlib
import logging

MIN_VALUE = 1e-3
MAX_VALUE = 1e7
ALLOWED = 1e16


def make_it_square(cost_matrix):

    size = max(cost_matrix.shape)
    new_cost_matrix = np.ones((size, size)) * MAX_VALUE
    new_cost_matrix[0 : cost_matrix.shape[0], 0 : cost_matrix.shape[1]] = cost_matrix
    return new_cost_matrix


def modify_cost_matrix_for_max_cost_assignment(cost_matrix):

    # Refer this doc to understand cost matrix modification http://dlib.net/python/index.html#dlib_pybind11.max_cost_assignment
    # MAX_VALUE/MIN_VALUE cannot be greater than 1e16 for convergence

    cost_matrix = make_it_square(cost_matrix)
    cost_matrix[cost_matrix < MIN_VALUE] = MIN_VALUE
    cost_matrix[cost_matrix > MAX_VALUE] = MAX_VALUE

    max_cost_matrix = np.reciprocal(cost_matrix)

    return max_cost_matrix


def hungarian_assignment(cost_matrix, pickups, sherpas):

    """
    ### COST MATRIX DESCRIPTION  ###
    ROWS represents TASKS (pickups)
    COLUMNS represent Agents (mules)

    Return:
     - Matches each task to an agent
    """

    assignment = {}
    cost_matrix = modify_cost_matrix_for_max_cost_assignment(cost_matrix)
    dlib_mat = dlib.matrix(cost_matrix)
    dlib_assignments = dlib.max_cost_assignment(dlib_mat)

    for i in range(0, len(dlib_assignments)):
        try:
            if cost_matrix[i, dlib_assignments[i]] == (1 / MAX_VALUE):
                # logging.info("dummy assignment route_length is infinity")
                continue
            assignment.update({pickups[i]: sherpas[dlib_assignments[i]]})
        except Exception as e:
            logging.info(f"hungarian assignment exception: {e}")

    return assignment, dlib_assignments
