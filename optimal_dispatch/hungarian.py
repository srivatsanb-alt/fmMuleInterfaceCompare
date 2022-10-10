import numpy as np
import dlib
import logging


def make_it_square(cost_matrix):
    size = max(cost_matrix.shape)
    new_cost_matrix = np.ones((size, size)) * np.inf
    new_cost_matrix[0 : cost_matrix.shape[0], 0 : cost_matrix.shape[1]] = cost_matrix
    return new_cost_matrix


def hungarian_assignment(cost_matrix, pickups, sherpas):
    assignment = {}
    cost_matrix = make_it_square(cost_matrix)
    dlib_mat = dlib.matrix(cost_matrix)
    dlib_assignments = dlib.max_cost_assignment(dlib_mat)

    for i in range(0, len * dlib_assignments):
        try:
            assignment.update({pickups[i]: sherpas[dlib_assignments[i]]})
        except Exception as e:
            logging.info(f"dummy assignment {e}")

    return assignment
