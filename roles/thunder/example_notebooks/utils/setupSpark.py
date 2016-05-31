def initSpark(nbBackend):
    import os
    if nbBackend == 'openstack':
        os.environ['SPARK_HOME'] = "/usr/local/spark"

    # setup Spark
    import findspark # SPARK_HOME needs to be set for import of findspark
    findspark.init()
    import pyspark
    from pyspark import SparkContext

    if nbBackend == 'local':
        # start a Spark context - Local machine
        master = 'local'
    elif nbBackend == 'openstack':
        # start a Spark context - OpenStack cluster
        master = 'spark://sparkcluster-controller001:7077'
    else:
        print "Backend " + nbBackend + " not known"
    try:
        sc = SparkContext(master=master)
        return sc
    except ValueError as exception:
        print "Could not create SparkContext. Maybe it exists already?"
