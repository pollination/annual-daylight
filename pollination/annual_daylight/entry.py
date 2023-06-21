from pollination_dsl.dag import Inputs, DAG, task, Outputs
from dataclasses import dataclass

# input/output alias
from pollination.alias.inputs.model import hbjson_model_grid_input
from pollination.alias.inputs.wea import wea_input_timestep_check
from pollination.alias.inputs.north import north_input
from pollination.alias.inputs.radiancepar import rad_par_annual_input, \
    daylight_thresholds_input
from pollination.alias.inputs.grid import grid_filter_input, \
    min_sensor_count_input, cpu_count
from pollination.alias.inputs.schedule import schedule_csv_input
from pollination.alias.outputs.daylight import daylight_autonomy_results, \
    continuous_daylight_autonomy_results, \
    udi_results, udi_lower_results, udi_upper_results


from ._prepare_folder import AnnualDaylightPrepareFolder
from ._raytracing import AnnualDaylightRayTracing
from ._post_process import AnnualDaylightPostProcess


@dataclass
class AnnualDaylightEntryPoint(DAG):
    """Annual daylight entry point."""

    # inputs
    north = Inputs.float(
        default=0,
        description='A number for rotation from north.',
        spec={'type': 'number', 'minimum': 0, 'maximum': 360},
        alias=north_input
    )

    cpu_count = Inputs.int(
        default=50,
        description='The maximum number of CPUs for parallel execution. This will be '
        'used to determine the number of sensors run by each worker.',
        spec={'type': 'integer', 'minimum': 1},
        alias=cpu_count
    )

    min_sensor_count = Inputs.int(
        description='The minimum number of sensors in each sensor grid after '
        'redistributing the sensors based on cpu_count. This value takes '
        'precedence over the cpu_count and can be used to ensure that '
        'the parallelization does not result in generating unnecessarily small '
        'sensor grids. The default value is set to 1, which means that the '
        'cpu_count is always respected.', default=500,
        spec={'type': 'integer', 'minimum': 1},
        alias=min_sensor_count_input
    )

    radiance_parameters = Inputs.str(
        description='The radiance parameters for ray tracing.',
        default='-ab 2 -ad 5000 -lw 2e-05 -dr 0',
        alias=rad_par_annual_input
    )

    grid_filter = Inputs.str(
        description='Text for a grid identifier or a pattern to filter the sensor grids '
        'of the model that are simulated. For instance, first_floor_* will simulate '
        'only the sensor grids that have an identifier that starts with '
        'first_floor_. By default, all grids in the model will be simulated.',
        default='*',
        alias=grid_filter_input
    )

    model = Inputs.file(
        description='A Honeybee Model JSON file (HBJSON) or a Model pkl (HBpkl) file. '
        'This can also be a zipped version of a Radiance folder, in which case this '
        'recipe will simply unzip the file and simulate it as-is.',
        extensions=['json', 'hbjson', 'pkl', 'hbpkl', 'zip'],
        alias=hbjson_model_grid_input
    )

    wea = Inputs.file(
        description='Wea file.',
        extensions=['wea'],
        alias=wea_input_timestep_check
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

    @task(template=AnnualDaylightPrepareFolder)
    def prepare_folder_annual_daylight(
        self, north=north, cpu_count=cpu_count, min_sensor_count=min_sensor_count,
        grid_filter=grid_filter, model=model, wea=wea
        ):
        return [
            {
                'from': AnnualDaylightPrepareFolder()._outputs.model_folder,
                'to': 'model'
            },
            {
                'from': AnnualDaylightPrepareFolder()._outputs.resources,
                'to': 'resources'
            },
            {
                'from': AnnualDaylightPrepareFolder()._outputs.results,
                'to': 'results'
            },
            {
                'from': AnnualDaylightPrepareFolder()._outputs.sensor_grids
            }
        ]

    @task(
        template=AnnualDaylightRayTracing,
        needs=[prepare_folder_annual_daylight],
        loop=prepare_folder_annual_daylight._outputs.sensor_grids,
        sub_folder='initial_results',
        sub_paths={
            'octree_file': 'scene.oct',
            'sensor_grid': 'grid/{{item.full_id}}.pts',
            'sky_matrix': 'sky.mtx',
            'sky_dome': 'sky.dome',
            'bsdfs': 'bsdf',
            'sun_up_hours': 'sun-up-hours.txt'
        }
    )
    def annual_daylight_raytracing(
        self,
        radiance_parameters=radiance_parameters,
        octree_file=prepare_folder_annual_daylight._outputs.resources,
        grid_name='{{item.full_id}}',
        sensor_grid=prepare_folder_annual_daylight._outputs.resources,
        sensor_count='{{item.count}}',
        sky_matrix=prepare_folder_annual_daylight._outputs.resources,
        sky_dome=prepare_folder_annual_daylight._outputs.resources,
        bsdfs=prepare_folder_annual_daylight._outputs.model_folder,
        sun_up_hours=prepare_folder_annual_daylight._outputs.results,
        schedule=schedule,
        thresholds=thresholds
    ):
        pass

    @task(
        template=AnnualDaylightPostProcess,
        needs=[prepare_folder_annual_daylight, annual_daylight_raytracing],
        sub_paths={
            'dist_info': 'grid/_redist_info.json',
            'grids_info': 'grids_info.json'
        }
    )
    def post_process_annual_daylight(
        self, initial_results='initial_results',
        dist_info=prepare_folder_annual_daylight._outputs.resources,
        grids_info=prepare_folder_annual_daylight._outputs.results,
        model=model
        ):
        return [
            {
                'from': AnnualDaylightPostProcess()._outputs.metrics,
                'to': 'metrics'
            }
        ]

    visualization = Outputs.file(
        source='visualization.vsf',
        description='Result visualization in VisualizationSet format.'
    )

    metrics = Outputs.folder(
        source='metrics', description='Annual metrics folder.'
    )

    da = Outputs.folder(
        source='metrics/da', description='Daylight autonomy results.',
        alias=daylight_autonomy_results
    )

    cda = Outputs.folder(
        source='metrics/cda', description='Continuous daylight autonomy results.',
        alias=continuous_daylight_autonomy_results
    )

    udi = Outputs.folder(
        source='metrics/udi', description='Useful daylight illuminance results.',
        alias=udi_results
    )

    udi_lower = Outputs.folder(
        source='metrics/udi_lower', description='Results for the percent of time that '
        'is below the lower threshold of useful daylight illuminance.',
        alias=udi_lower_results
    )

    udi_upper = Outputs.folder(
        source='metrics/udi_upper', description='Results for the percent of time that '
        'is above the upper threshold of useful daylight illuminance.',
        alias=udi_upper_results
    )
