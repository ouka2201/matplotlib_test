import tableauserverclient as TSC

from cndx_corp_batch.common.exceptions import BatchError


class TableauRefreshService:
    def __init__(self, server: TSC.Server, logger):
        self.server = server
        self.logger = logger

    def refresh_report_datasources(
        self, datasouce_name_list: set[str], report_type: str = None
    ):
        all_datasources, _ = self.server.datasources.get()

        refreshed = False

        for ds in all_datasources:
            if ds.name in datasouce_name_list:
                self.logger.info(
                    "refresh datasource: %s",
                    ds.name,
                )

                job = self.server.datasources.refresh(
                    datasource_item=ds,
                    incremental=True,
                )
                self.server.jobs.wait_for_job(job.id, timeout=3600)
                refreshed = True

        if not refreshed:
            raise BatchError(f"{report_type}のデータソースが見つかりません")
