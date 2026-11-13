def storeTags():

    tags = [
        "[Sample_Tags]Realistic/Realistic0",
        "[Sample_Tags]Realistic/Realistic1"
    ]

    values = system.tag.readBlocking(tags)

    for i,v in enumerate(values):

        system.db.runPrepUpdate(
            """
            INSERT INTO MachineTags
            (machineId,tagName,tagValue,tagTimestamp)
            VALUES (?,?,?,GETDATE())
            """,
            [
                "M001",
                tags[i],
                str(v.value)
            ],
            "MSSQL"
        )

storeTags()