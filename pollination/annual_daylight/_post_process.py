"""Post-process DAG for annual daylight."""
from dataclasses import dataclass
from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from pollination.honeybee_radiance_postprocess.grid import MergeFolderMetrics
from pollination.honeybee_radiance_postprocess.post_process import GridSummaryMetrics


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

    grid_metrics = Inputs.file(
        description='A JSON file with additional custom metrics to calculate.',
        path='grid_metrics.json', optional=True
    )

    @task(
        template=MergeFolderMetrics
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

    @task(
        template=GridSummaryMetrics,
        needs=[restructure_metrics]
    )
    def grid_summary_metrics(
        self, folder=restructure_metrics._outputs.output_folder,
        model=model, grids_info=grids_info, grid_metrics=grid_metrics,
        folder_level='sub-folder'
    ):
        return [
            {
                'from': GridSummaryMetrics()._outputs.grid_summary,
                'to': 'grid_summary.csv'
            }
        ]

    metrics = Outputs.folder(
        source='metrics', description='metrics folder.'
    )

    grid_summary = Outputs.file(
        source='grid_summary.csv', description='grid summary.'
    )
