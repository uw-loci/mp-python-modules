# -*- coding: utf-8 -*-
"""
Created on Wed Mar 21 09:38:19 2018

@author: mpinkert
"""
import mp_img_manip.bulk_img_processing as blk
import mp_img_manip.utility_functions as util

import mp_img_manip.itk.metadata as meta
import mp_img_manip.itk.transform as tran
import mp_img_manip.itk.process as proc
from mp_img_manip.itk.registration_plot import RegistrationPlot

import SimpleITK as sitk
import numpy as np
import os

from pathlib import Path

import matplotlib.pyplot as plt


def plot_overlay(fixed_image: sitk.Image, moving_image: sitk.Image, rotation: np.double,
                 type_of_transform='affine'):

    origin = moving_image.GetOrigin()

    deg_to_rad = 2 * np.pi / 360
    angle = rotation * deg_to_rad

    if type_of_transform == 'euler':
        transform = sitk.Euler2DTransform()
        transform.SetAngle(angle)
    else:
        transform = sitk.AffineTransform(2)
        transform.Rotate(0, 1, rotation * deg_to_rad, pre=True)

    rotated_image = sitk.Resample(moving_image, fixed_image, transform,
                                  sitk.sitkLinear, 0.0,
                                  moving_image.GetPixelIDValue())

    fig, ax = plt.subplots()
    ax.set_title('Rotation = {}, Origin = {}'.format(rotation, origin))
    ax.imshow(proc.overlay_images(fixed_image, rotated_image))

    # mng = plt.get_current_fig_manager()
    # geom = mng.window.geometry().getRect()
    # mng.window.setGeometry(-1800, 100, geom[2], geom[3])

    # fig.canvas.draw()
    # fig.canvas.flush_events()
    # plt.pause(0.1)
    plt.show()


def register(fixed_image, moving_image, reg_plot: RegistrationPlot,
             scale=3, iterations=10,
             fixed_mask=None, moving_mask=None, rotation=0,
             learning_rate=50, min_step=0.01, gradient_tolerance=1E-5,
             type_of_transform='affine'):
    """Perform an affine registration using MI and RSGD over up to 4 scales
    
    Uses mutual information and regular step gradient descent
    
    Inputs:
    fixed_image -- The image that is registered to
    moving_image -- The image that is being registered
    scale -- how many resolution scales the function uses
    iterations -- Iterations per scale before the function stops
    fixed_mask -- Forces calculations over part of the fixed image
    moving_mask -- Forces calculations over part of the moving image
    rotation -- Pre rotation in degrees, to assist in registration
    
    Outputs:
    transform -- The calculated image transform for registration
    metric -- The mutual information value at the stopping poin
    stop -- the stopping condition of the optimizer
    """

    fixed_image = sitk.Cast(fixed_image, sitk.sitkFloat32)
    moving_image = sitk.Cast(moving_image, sitk.sitkFloat32)

    registration_method = sitk.ImageRegistrationMethod()

    # Similarity metric settings.|
    registration_method.SetMetricAsMattesMutualInformation()
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(1)

    registration_method.SetInterpolator(sitk.sitkLinear)

    if fixed_mask:
        registration_method.SetMetricFixedMask(fixed_mask)

    if moving_mask:
        registration_method.SetMetricMovingMask(moving_mask)

    # Optimizer settings.
    registration_method.SetOptimizerAsRegularStepGradientDescent(learningRate=learning_rate, minStep=min_step,
                                                                 numberOfIterations=iterations,
                                                                 gradientMagnitudeTolerance=gradient_tolerance)

    registration_method.SetOptimizerScalesFromPhysicalShift()

    # Setup for the multi-resolution framework.
    shrink_factors = [8, 4, 2, 1]
    smoothing_sigmas = [2, 2, 1, 1]
    if scale > 4:
        scale = 4
        print('Warning, scale was set higher than the maximum value of 4')

    registration_method.SetShrinkFactorsPerLevel(shrink_factors[(4-scale):])
    registration_method.SetSmoothingSigmasPerLevel(smoothing_sigmas[(4-scale):])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    deg_to_rad = 2*np.pi/360
    angle = rotation*deg_to_rad

    if type_of_transform == 'euler':
        transform = sitk.Euler2DTransform()
        transform.SetAngle(angle)
    else:
        transform = sitk.AffineTransform(2)
        transform.Rotate(0, 1, angle, pre=True)

    registration_method.SetInitialTransform(transform)

    registration_method.AddCommand(sitk.sitkMultiResolutionIterationEvent, reg_plot.update_idx_resolution_switch)
    registration_method.AddCommand(sitk.sitkIterationEvent, lambda: reg_plot.update_plot(
        registration_method.GetMetricValue(), fixed_image, moving_image, transform))

    return (registration_method.Execute(fixed_image, moving_image),
            registration_method.GetMetricValue(),
            registration_method.GetOptimizerStopConditionDescription())


def query_good_registration(fixed_image, moving_image,
                            transform, metric, stop):

    print('\nFinal metric value: {0}'.format(metric))
    print('\n{0}'.format(stop))

    transform_params = transform.GetParameters()
    matrix = np.array([transform_params[0:2], transform_params[2:4]])
    translation = np.array(transform_params[4:6])
    print('\nTransform Matrix: \n{0}'.format(matrix))
    print('\nTransform Translation: \n{0}'.format(translation))

    plt.show()

    return util.yes_no('Is this registration good? [y/n] >>> ')


def query_pre_rotation(fixed_image, moving_image, initial_rotation, type_of_transform):
    """Ask if the user wants a new 2D ITK origin based on image overlay"""

    plot_overlay(fixed_image, moving_image, initial_rotation, type_of_transform=type_of_transform)

    change_rotation = util.yes_no('Do you want to change the rotation? [y/n] >>> ')

    rotation = initial_rotation

    if change_rotation:
        while True:
            rotation = util.query_float('Enter new rotation (degrees):')

            plot_overlay(fixed_image, moving_image, rotation, type_of_transform=type_of_transform)

            # bug: The image does not show up till after the question
            if util.yes_no('Is this rotation good? [y/n] >>> '): break

    return rotation


def query_origin_change(fixed_image, moving_image, rotation, type_of_transform):
    """Ask if the user wants a new 2D ITK origin based on image overlay"""

    change_origin = util.yes_no('Do you want to change the origin? [y/n] >>> ')
    origin = moving_image.GetOrigin()

    # todo: have it change the origin file too....

    if change_origin:
        while True:
            print('Current origin: ' + str(origin))
            new_origin_x = util.query_int('Enter new X origin: ')
            new_origin_y = util.query_int('Enter new Y origin: ')

            new_origin = (new_origin_x, new_origin_y)

            moving_image.SetOrigin(new_origin)
            plot_overlay(fixed_image, moving_image, rotation, type_of_transform=type_of_transform)

            # bug: The image does not show up till after the question
            if util.yes_no('Is this origin good? [y/n] >>> '): break

        return new_origin
    else:
        return origin


def rgb_to_2d_img(moving_image):
    """Convert an RGB to grayscale image by extracting the average intensity, filtering out white light >230 avg"""
    array = sitk.GetArrayFromImage(moving_image)
    array_2d = np.average(array, 2)
    array_2d[array_2d > 0.9*np.max(array)] = 0

    moving_image_2d = sitk.GetImageFromArray(array_2d)
    spacing_2d = moving_image.GetSpacing()[:2]
    moving_image_2d.SetSpacing(spacing_2d)

    origin_2d = moving_image.GetOrigin()[:2]
    moving_image_2d.SetOrigin(origin_2d)
    return moving_image_2d


def write_image(registered_image, registered_path, rotation):
    """

    :param registered_image: the final registered image
    :param registered_path: the path to save the registered image to
    :param rotation: rotation of the final image, typically 0
    :return:
    """
    sitk.WriteImage(registered_image, str(registered_path))

    meta.write_image_parameters(registered_path,
                                registered_image.GetSpacing(),
                                registered_image.GetOrigin(),
                                rotation)


def supervised_register_images(fixed_path: Path, moving_path: Path,
                               iterations=200, scale=4, type_of_transform='affine'):
    """

    :param fixed_path: path to the image that is being registered to
    :param moving_path: path to the image that is being transformed and registered
    :param iterations: how many iterations the algorithm calculates the metric at each resolution scale
    :param scale: how many resolution scales there are
    :param type_of_transform: the type of registration/transform, e.g. affine or euler
    :return:
    """

    fixed_image = meta.setup_image(fixed_path, change_origin=False)
    moving_image, rotation = meta.setup_image(moving_path, return_rotation=True)
    print('\nRegistering ' + os.path.basename(moving_path) + ' to '
          + os.path.basename(fixed_path))

    moving_image_is_rgb = moving_image.GetNumberOfComponentsPerPixel() > 1
    if moving_image_is_rgb:
        moving_image_2d = rgb_to_2d_img(moving_image)
    else:
        moving_image_2d = moving_image

    while True:
        rotation = query_pre_rotation(fixed_image, moving_image_2d, rotation)
        moving_image_2d.SetOrigin(query_origin_change(fixed_image, moving_image_2d, rotation))

        reg_plot = RegistrationPlot(fixed_image, moving_image_2d)
        (transform, metric, stop) = register(fixed_image, moving_image_2d, reg_plot,
                                             iterations=iterations, scale=scale, rotation=rotation,
                                             type_of_transform=type_of_transform)

        if query_good_registration(fixed_image, moving_image_2d, transform, metric, stop):
            break

    origin = moving_image.GetOrigin()
    meta.write_image_parameters(moving_path, moving_image.GetSpacing(), origin, rotation)

    registered_image = sitk.Resample(moving_image, fixed_image,
                                     transform, sitk.sitkLinear,
                                     0.0, moving_image.GetPixelID())

    plt.close('all')

    return registered_image, origin, transform, metric, stop, rotation


def bulk_supervised_register_images(fixed_dir, moving_dir,
                                    output_dir, output_suffix,
                                    write_output=True, write_transform=True, type_of_transform='affine',
                                    iterations=100, scale=3,
                                    skip_existing_images=True):
    """

    :param fixed_dir: directory holding the images that are being registered to
    :param moving_dir: directory holding the images that will be registered
    :param output_dir: directory to save the output images
    :param output_suffix: base name of the output images
    :param write_output: whether or not to actually write the output image
    :param write_transform: whether or not to write down the transform that produced the output
    :param type_of_transform: what type of registration, e.g. affine or euler
    :param iterations: how many times will the algorithm calcluate the metric before switching resolutions/ending
    :param scale: how many resolution scales the algorithm measures at
    :param skip_existing_images: whether to skip images that already have a transform/output image
    :return:
    """

    (fixed_path_list, moving_path_list) = blk.find_shared_images(
        fixed_dir, moving_dir)

    for i in range(0, np.size(fixed_path_list)):
        registered_path = blk.create_new_image_path(moving_path_list[i], output_dir, output_suffix)
        if registered_path.exists() and skip_existing_images:
            continue
        
        registered_image, origin, transform, metric, stop, rotation = \
            supervised_register_images(fixed_path_list[i], moving_path_list[i],
                                       type_of_transform=type_of_transform, iterations=iterations, scale=scale)

        if write_output:
            write_image(registered_image, registered_path, rotation)

        if write_transform:
            tran.write_transform(registered_path, origin, transform, metric, stop, rotation)




