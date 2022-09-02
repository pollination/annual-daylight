from pollination_dsl.dag import Inputs, DAG, task, Outputs
from dataclasses import dataclass
from pollination.honeybee_radiance.sun import CreateSunMatrix, ParseSunUpHours
from pollination.honeybee_radiance.translate import CreateRadianceFolderGrid
from pollination.honeybee_radiance.sky import CreateSkyDome, CreateSkyMatrix
from pollination.honeybee_radiance.multiphase import PrepareMultiphase
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightMetrics

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

from .two_phase.entry import TwoPhase


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

    @task(template=CreateSunMatrix)
    def generate_sunpath(self, north=north, wea=wea):
        """Create sunpath for sun-up-hours."""
        return [
            {'from': CreateSunMatrix()._outputs.sunpath,
             'to': 'resources/sunpath.mtx'},
            {
                'from': CreateSunMatrix()._outputs.sun_modifiers,
                'to': 'resources/suns.mod'
            }
        ]

    @task(template=CreateRadianceFolderGrid)
    def create_rad_folder(self, input_model=model, grid_filter=grid_filter):
        """Translate the input model to a radiance folder."""
        return [
            {
                'from': CreateRadianceFolderGrid()._outputs.model_folder,
                'to': 'model'
            },
            {
                'from': CreateRadianceFolderGrid()._outputs.bsdf_folder,
                'to': 'model/bsdf'
            },
            {
                'from': CreateRadianceFolderGrid()._outputs.sensor_grids_file,
                'to': 'results/grids_info.json'
            },
            {
                'from': CreateRadianceFolderGrid()._outputs.sensor_grids,
                'description': 'Sensor grids information.'
            }
        ]

    @task(template=CreateSkyDome)
    def create_sky_dome(self):
        """Create sky dome for daylight coefficient studies."""
        return [
            {'from': CreateSkyDome()._outputs.sky_dome, 'to': 'resources/sky.dome'}
        ]

    @task(template=CreateSkyMatrix)
    def create_total_sky(self, north=north, wea=wea, sun_up_hours='sun-up-hours'):
        return [
            {'from': CreateSkyMatrix()._outputs.sky_matrix,
             'to': 'resources/sky.mtx'}
        ]

    @task(template=CreateSkyMatrix)
    def create_direct_sky(
        self, north=north, wea=wea, sky_type='sun-only', sun_up_hours='sun-up-hours'
    ):
        return [
            {
                'from': CreateSkyMatrix()._outputs.sky_matrix,
                'to': 'resources/sky_direct.mtx'
            }
        ]

    @task(template=ParseSunUpHours, needs=[generate_sunpath])
    def parse_sun_up_hours(self, sun_modifiers=generate_sunpath._outputs.sun_modifiers):
        return [
            {
                'from': ParseSunUpHours()._outputs.sun_up_hours,
                'to': 'results/sun-up-hours.txt'
            }
        ]

    @task(template=PrepareMultiphase, needs=[create_rad_folder, generate_sunpath])
    def prepare_multiphase(
        self, model=create_rad_folder._outputs.model_folder,
        sunpath=generate_sunpath._outputs.sunpath, phase=2, cpu_count=cpu_count,
        cpus_per_grid=3, min_sensor_count=min_sensor_count, static='include'
    ):
        return [
            {
                'from': PrepareMultiphase()._outputs.scene_folder,
                'to': 'resources/dynamic/octree'
            },
            {
                'from': PrepareMultiphase()._outputs.grid_folder,
                'to': 'resources/dynamic/grid'
            },
            {
                'from': PrepareMultiphase()._outputs.two_phase_info
            },
            {   'from': PrepareMultiphase()._outputs.grid_states_file,
                'to': 'results/grid_states.json'
            }
        ]

    @task(
        template=TwoPhase,
        loop=prepare_multiphase._outputs.two_phase_info,
        needs=[
            create_rad_folder, prepare_multiphase, create_total_sky,
            create_direct_sky, create_sky_dome, generate_sunpath
        ],
        sub_folder='calcs/2_phase/{{item.identifier}}',
        sub_paths={
            'octree_file': '{{item.octree}}',
            'octree_file_direct': '{{item.octree_direct}}',
            'octree_file_with_suns': '{{item.octree_direct_sun}}',
            'sensor_grids_folder': '{{item.sensor_grids_folder}}'
        }
    )
    def calculate_two_phase_matrix(
        self,
        identifier='{{item.identifier}}',
        light_path='{{item.light_path}}',
        radiance_parameters=radiance_parameters,
        sensor_grids_info='{{item.sensor_grids_info}}',
        sensor_grids_folder=prepare_multiphase._outputs.grid_folder,
        octree_file=prepare_multiphase._outputs.scene_folder,
        octree_file_direct=prepare_multiphase._outputs.scene_folder,
        octree_file_with_suns=prepare_multiphase._outputs.scene_folder,
        sky_dome=create_sky_dome._outputs.sky_dome,
        total_sky=create_total_sky._outputs.sky_matrix,
        direct_sky=create_direct_sky._outputs.sky_matrix,
        sun_modifiers=generate_sunpath._outputs.sun_modifiers,
        bsdf_folder=create_rad_folder._outputs.bsdf_folder,
        results_folder='../../../results'
    ):
        pass

    @task(
        template=AnnualDaylightMetrics,
        needs=[calculate_two_phase_matrix]
    )
    def calculate_annual_metrics(
        self, folder='results', schedule=schedule, thresholds=thresholds
    ):
        return [
            {
                'from': AnnualDaylightMetrics()._outputs.annual_metrics,
                'to': 'metrics'
            }
        ]

    results = Outputs.folder(
        source='results', description='Folder with raw result files (.ill) that '
        'contain illuminance matrices for each sensor at each timestep of the analysis.'
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
