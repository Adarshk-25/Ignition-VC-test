def doGet(request, session):

    logger = system.util.getLogger("MES-REST")

    try:

        folderPath = "[Sample_Tags]Realistic"

        browseResults = system.tag.browse(folderPath).getResults()

        tagPaths = []

        for tag in browseResults:

            if str(tag['tagType']) == "AtomicTag":
                tagPaths.append(str(tag['fullPath']))

        values = system.tag.readBlocking(tagPaths)

        tags = []

        for i in range(len(tagPaths)):

            tagName = tagPaths[i].split("/")[-1]

            tags.append({
                "name": tagName,
                "path": tagPaths[i],
                "value": values[i].value,
                "quality": str(values[i].quality),
                "timestamp": str(values[i].timestamp)
            })

        return {
            "json": {
                "folder": folderPath,
                "tagCount": len(tags),
                "tags": tags,
                "timestamp": str(system.date.now())
            }
        }

    except Exception as e:

        logger.error(str(e))

        return {
            "json": {
                "status": "ERROR",
                "message": str(e)
            },
            "status": 500
        }