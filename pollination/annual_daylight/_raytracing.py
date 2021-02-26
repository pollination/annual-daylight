"""Raytracing DAG for annual daylight."""

from pollination_dsl.dag import Inputs, DAG, task
from dataclasses import dataclass

from pollination.honeybee_radiance.grid import SplitGrid, MergeFiles
from pollination.honeybee_radiance.contrib import DaylightContribution
from pollination.honeybee_radiance.coefficient import DaylightCoefficient
from pollination.honeybee_radiance.sky import AddRemoveSkyMatrix


@dataclass
class AnnualDaylightRayTracing(DAG):
    # inputs

    sensor_count = Inputs.int(
        default=200,
        description='The maximum number of grid points per parallel execution',
        spec={'type': 'integer', 'minimum': 1}
    )

    radiance_parameters = Inputs.str(
        description='The radiance parameters for ray tracing',
        default='-ab 2 -ad 5000 -lw 2e-05'
    )

    octree_file_with_suns = Inputs.file(
        description='A Radiance octree file with suns.',
        extensions=['oct']
    )

    octree_file = Inputs.file(
        description='A Radiance octree file.',
        extensions=['oct']
    )

    grid_name = Inputs.str(
        description='Sensor grid file name. This is useful to rename the final result '
        'file to {grid_name}.res'
    )

    sensor_grid = Inputs.file(
        description='Sensor grid file.',
        extensions=['pts']
    )

    sun_modifiers = Inputs.file(
        description='A file with sun modifiers.'
    )

    sky_matrix = Inputs.file(
        description='Path to total sky matrix file.'
    )

    sky_matrix_direct = Inputs.file(
        description='Path to direct skymtx file (i.e. gendaymtx -d).'
    )

    sky_dome = Inputs.file(
        description='Path to sky dome file.'
    )

    @task(template=SplitGrid)
    def split_grid(self, sensor_count=sensor_count, input_grid=sensor_grid):
        return [
            {'from': SplitGrid()._outputs.grids_list},
            {'from': SplitGrid()._outputs.output_folder, 'to': 'sub_grids'}
        ]

    @task(
        template=DaylightContribution, needs=[split_grid],
        loop=split_grid._outputs.grids_list, sub_folder='direct_sunlight',
        sub_paths={'sensor_grid': '{{item.path}}'}
    )
    def direct_sunlight(
        self,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -faf -ab 0 -dc 1.0 -dt 0.0 -dj 0.0 -dr 0',
        sensor_count='{{item.count}}', modifiers=sun_modifiers,
        sensor_grid=split_grid._outputs.output_folder,
        scene_file=octree_file_with_suns
            ):
        return [
            {
                'from': DaylightContribution()._outputs.result_file,
                'to': '{{item.name}}.ill'
            }
        ]

    @task(
        template=DaylightCoefficient, needs=[split_grid],
        loop=split_grid._outputs.grids_list, sub_folder='direct_sky',
        sub_paths={'sensor_grid': '{{item.path}}'}
    )
    def direct_sky(
        self,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -ab 1 -c 1 -faf',
        sensor_count='{{item.count}}',
        sky_matrix=sky_matrix_direct, sky_dome=sky_dome,
        sensor_grid=split_grid._outputs.output_folder,
        scene_file=octree_file
            ):
        return [
            {
                'from': DaylightContribution()._outputs.result_file,
                'to': '{{item.name}}.ill'
            }
        ]

    @task(
        template=DaylightCoefficient, needs=[split_grid],
        loop=split_grid._outputs.grids_list, sub_folder='total_sky',
        sub_paths={'sensor_grid': '{{item.path}}'}
    )
    def total_sky(
        self,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1 -faf',
        sensor_count='{{item.count}}',
        sky_matrix=sky_matrix, sky_dome=sky_dome,
        sensor_grid=split_grid._outputs.output_folder,
        scene_file=octree_file
            ):
        return [
            {
                'from': DaylightContribution()._outputs.result_file,
                'to': '{{item.name}}.ill'
            }
        ]

    @task(
        template=AddRemoveSkyMatrix,
        needs=[split_grid, direct_sunlight, total_sky, direct_sky],
        loop=split_grid._outputs.grids_list, sub_folder='final'
    )
    def output_matrix_math(
        self,
        direct_sky_matrix='direct_sky/{{item.name}}.ill',
        total_sky_matrix='total_sky/{{item.name}}.ill',
        sunlight_matrix='direct_sunlight/{{item.name}}.ill',
        conversion='47.4 119.9 11.6'
            ):
        return [
            {
                'from': AddRemoveSkyMatrix()._outputs.results_file,
                'to': '{{item.name}}.ill'
            }
        ]

    @task(
        template=MergeFiles, needs=[output_matrix_math]
    )
    def merge_raw_results(self, name=grid_name, extension='.ill', folder='final'):
        return [
            {
                'from': MergeFiles()._outputs.result_file,
                'to': '../../results/{{self.name}}.ill'
            }
        ]
