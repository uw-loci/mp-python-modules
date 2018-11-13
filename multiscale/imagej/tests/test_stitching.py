import multiscale.imagej.stitching as stitch
import numpy as np
from pathlib import Path
import imagej
import pytest


class TestBigStitcher(object):
        def test_stitch_from_files(self):
                return

        def test_stitch_from_numpy(self, tmpdir, ij):
                outdir = tmpdir.mkdir('stitch')
                outdir = str(outdir).replace('\\', '/')
                
                array = np.random.rand(9, 128, 128)
                args = {
                        'define_dataset': '[Automatic Loader (Bioformats based)]',
                        'project_filename': 'dataset.xml',
                        'exclude': '10',
                        'pattern_0': 'Tiles',
                        'modify_voxel_size?': None,
                        'voxel_size_x': '0.5',
                        'voxel_size_y': '0.5',
                        'voxel_size_z': '0.5',
                        'voxel_size_unit': '\u03bcm',
                        'move_tiles_to_grid_(per_angle)?': '[Move Tile to Grid (Macro-scriptable)]',
                        'grid_type': '[Right & Down             ]',
                        'tiles_x': 3,
                        'tiles_y': 3,
                        'tiles_z': 1,
                        'overlap_x_(%)': '10',
                        'overlap_y_(%)': '10',
                        'overlap_z_(%)': '10',
                        'keep_metadata_rotation': None,
                        'how_to_load_images': '[Re-save as multiresolution HDF5]',
                        'dataset_save_path': outdir,
                        'subsampling_factors': '[{ {1,1,1}, {2,2,2}, {4,4,4} }]',
                        'hdf5_chunk_sizes': '[{ {16,16,16}, {16,16,16}, {16,16,16} }]',
                        'timepoints_per_partition': '1',
                        'setups_per_partition': '0',
                        'use_deflate_compression': None,
                        'export_path': outdir + '/dataset'
                }

                stitcher = stitch.BigStitcher(ij)
                stitcher.stitch_from_numpy(array, args, {})

                dataset_path = Path(outdir, 'dataset.h5')

                assert dataset_path.is_file()

                #todo : Add fuse args and fuse testing

        def test_save_numpy_images(self, tmpdir):
                array = np.random.rand(3, 2, 2)
                outdir = tmpdir.mkdir('stitch')
                stitcher = stitch.BigStitcher(True)
                stitcher._save_numpy_images(outdir, array)
                
                for idx in range(len(array)):
                        save_path = Path(outdir, 'Image_{}.tif'.format(idx))
                        assert save_path.is_file()