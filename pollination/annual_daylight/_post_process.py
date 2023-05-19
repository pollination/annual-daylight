"""Post-process DAG for annual daylight."""
from dataclasses import dataclass
from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from pollination.honeybee_radiance_postprocess.grid import MergeFolderData, \
    MergeFolderMetrics
from pollination.honeybee_display.translate import ModelToVis


@dataclass
class AnnualDaylightPostProcess(GroupedDAG):
    """Post-process for annual daylight."""

    # inputs
    model = Inputs.file(
        description='Input Honeybee model.',
        extensions=['json', 'hbjson', 'pkl', 'hbpkl', 'zip']
    )

    initial_results = Inputs.folder(
        description='Folder with initial results. This is the distributed '
        'results.',
        path='initial_results'
    )

    dist_info = Inputs.file(
        description='Distribution information file.',
        path='dist_info.json'
    )

    grids_info = Inputs.file(
        description='Grid information file.',
        path='grids_info.json'
    )

    @task(
        template=MergeFolderData,
        sub_paths={
            'input_folder': 'final'
        }
    )
    def restructure_results(
        self, input_folder=initial_results, extension='ill',
        dist_info=dist_info
    ):
        return [
            {
                'from': MergeFolderData()._outputs.output_folder,
                'to': 'results/__static_apertures__/default/total'
            }
        ]

    @task(
        template=MergeFolderMetrics,
        sub_paths={
            'input_folder': 'metrics'
        }
    )
    def restructure_metrics(
        self, input_folder=initial_results,
        dist_info=dist_info,
        grids_info=grids_info
    ):
        return [
            {
                'from': MergeFolderMetrics()._outputs.output_folder,
                'to': 'metrics'
            }
        ]

    @task(template=ModelToVis, needs=[restructure_metrics])
    def create_vsf(
        self, model=model, grid_data='metrics', active_grid_data='udi',
        output_format='vsf'
    ):
        return [
            {
                'from': ModelToVis()._outputs.output_file,
                'to': 'visualization.vsf'
            }
        ]

    results = Outputs.folder(
        source='results', description='results folder.'
    )

    metrics = Outputs.folder(
        source='metrics', description='metrics folder.'
    )

    visualization = Outputs.file(
        source='visualization.vsf',
        description='Annual Daylight result visualization in VisualizationSet format.'
    )
