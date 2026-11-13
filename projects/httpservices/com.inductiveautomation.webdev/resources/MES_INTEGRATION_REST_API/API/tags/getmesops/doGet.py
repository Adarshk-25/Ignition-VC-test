def doGet(request, session):
	

    import system
    import traceback

    logger = system.util.getLogger("GETTAGS")

    try:

        logger.info("GET TAG API Called")

        params = request.get("params", {})

        machineId = str(
            params.get("machineId", "")
        ).strip()

        tagName = str(
            params.get("tagName", "")
        ).strip()

        logger.info(
            "machineId = %s , tagName = %s" %
            (machineId, tagName)
        )

        # Base Query
        query = """
        SELECT TOP 74
            machineId,
            tagName,
            tagValue,
            tagTimestamp
        FROM MachineTags
        """

        conditions = []
        queryParams = []

        # Dynamic WHERE conditions

        if machineId != "":

            conditions.append(
                "machineId = ?"
            )

            queryParams.append(
                machineId
            )

        if tagName != "":

            conditions.append(
                "tagName = ?"
            )

            queryParams.append(
                tagName
            )

        # Add WHERE if conditions exist
        if len(conditions) > 0:

            query += " WHERE "

            query += " AND ".join(
                conditions
            )

        # Add sorting
        query += """
        ORDER BY tagTimestamp DESC
        """

        logger.info(
            "Final Query: " + query
        )

        logger.info(
            "Query Params: " +
            str(queryParams)
        )

        # Execute Query
        rows = system.db.runPrepQuery(
            query,
            queryParams,
            "Dev_MSSQL_Server"
        )

        logger.info(
            "Rows fetched: " +
            str(len(rows))
        )

        data = []

        for row in rows:

            item = {

                "machineId":
                    str(row["machineId"]),

                "tagName":
                    str(row["tagName"]),

                "tagValue":
                    str(row["tagValue"]),

                "tagTimestamp":
                    str(row["tagTimestamp"])

            }

            data.append(item)

        response = {

            "status": "success",

            "count":
                len(data),

            "filters": {

                "machineId":
                    machineId,

                "tagName":
                    tagName

            },

            "data":
                data

        }

        logger.info(
            "Returning API Response"
        )

        return {

            "json":
                response

        }

    except Exception as e:

        logger.error(
            traceback.format_exc()
        )

        return {

            "json": {

                "status": "error",

                "message":
                    str(e)

            }

        }