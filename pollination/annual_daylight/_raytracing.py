"""Ray tracing DAG for annual daylight."""
from pollination_dsl.dag import Inputs, DAG, task
from dataclasses import dataclass

from pollination.honeybee_radiance.coefficient import DaylightCoefficient
from pollination.honeybee_radiance_postprocess.post_process import \
    AnnualDaylightMetricsFile

# input/output alias
from pollination.alias.inputs.radiancepar import daylight_thresholds_input
from pollination.alias.inputs.schedule import schedule_csv_input


@dataclass
class AnnualDaylightRayTracing(DAG):
    # inputs
    radiance_parameters = Inputs.str(
        description='The radiance parameters for ray tracing',
        default='-ab 2 -ad 5000 -lw 2e-05'
    )

    octree_file = Inputs.file(
        description='A Radiance octree file.',
        extensions=['oct']
    )

    grid_name = Inputs.str(
        description='Sensor grid file name. This is useful to rename the final result '
        'file to {grid_name}.ill'
    )

    sensor_grid = Inputs.file(
        description='Sensor grid file.',
        extensions=['pts']
    )

    sensor_count = Inputs.int(
        description='Number of sensors in the input sensor grid.'
    )

    sky_matrix = Inputs.file(
        description='Path to total sky matrix file.'
    )

    sky_dome = Inputs.file(
        description='Path to sky dome file.'
    )

    bsdfs = Inputs.folder(
        description='Folder containing any BSDF files needed for ray tracing.',
        optional=True
    )

    sun_up_hours = Inputs.file(
        description='A text file that includes all the sun up hours. Each '
        'hour is separated by a new line.'
    )

    schedule = Inputs.file(
        description='Path to an annual schedule file. Values should be 0-1 separated '
        'by new line. If not provided an 8-5 annual schedule will be created.',
        extensions=['txt', 'csv'], optional=True, alias=schedule_csv_input
    )

    thresholds = Inputs.str(
        description='A string to change the threshold for daylight autonomy and useful '
        'daylight illuminance. Valid keys are -t for daylight autonomy threshold, -lt '
        'for the lower threshold for useful daylight illuminance and -ut for the upper '
        'threshold. The default is -t 300 -lt 100 -ut 3000. The order of the keys is '
        'not important and you can include one or all of them. For instance if you only '
        'want to change the upper threshold to 2000 lux you should use -ut 2000 as '
        'the input.', default='-t 300 -lt 100 -ut 3000',
        alias=daylight_thresholds_input
    )

    @task(template=DaylightCoefficient)
    def total_sky(
        self,
        name=grid_name,
        radiance_parameters=radiance_parameters,
        fixed_radiance_parameters='-aa 0.0 -I -c 1 -faf',
        sensor_count=sensor_count,
        sky_matrix=sky_matrix,
        sky_dome=sky_dome,
        sensor_grid=sensor_grid,
        scene_file=octree_file,
        conversion='47.4 119.9 11.6',
        bsdf_folder=bsdfs
    ):
        return [
            {
                'from': DaylightCoefficient()._outputs.result_file,
                'to': 'final/{{self.name}}.ill'
            }
        ]

    @task(
        template=AnnualDaylightMetricsFile,
        needs=[total_sky]
    )
    def annual_metrics_file(
        self,
        file=total_sky._outputs.result_file,
        sun_up_hours=sun_up_hours,
        schedule=schedule,
        thresholds=thresholds,
        grid_name=grid_name
    ):
        return [
            {
                'from': AnnualDaylightMetricsFile()._outputs.annual_metrics,
                'to': 'metrics'
            }
        ]
