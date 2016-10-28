def initSpark(nb_backend, app_name='pyspark', spark_instances=2, executor_cores= 2, max_cores=8, executor_memory='10G'):
    """
    Configure and create SparkContext.

    nb_backend ... backend for notebook ('local' or 'openstack')
    app_name ... name of the Spark application
    spark_instances ... number of executor instances (e.g. number of workers)
    executor_cores ... the number of cores for each executor
    max_cores ... max. number of cores that can be used
    executor_memory ... memory per executor
    """

    # ressource settings
    # conf.set("spark.executor.instances", 4)
    # conf.set("spark.cores.max", 16)
    # conf.set("spark.executor.memory", "10G")
    # conf.set("spark.executor.cores", 3)

    import os
    if nb_backend == 'openstack':
        os.environ['SPARK_HOME'] = "/usr/local/spark"
        os.environ['SPARK_DRIVER_MEMORY'] = '10G'

    # setup Spark
    import findspark # SPARK_HOME needs to be set for import of findspark
    findspark.init()
    import pyspark
    from pyspark import SparkContext, SparkConf

    conf = SparkConf().setAppName(app_name)

    if nb_backend == 'local':
        # options for Spark on local machine
        master = 'local'
    elif nb_backend == 'openstack':
        # options for Spark on OpenStack cluster
        master = 'spark://sparkcluster-controller001:7077'
    else:
        print "Backend " + nb_backend + " not known"

    conf.setMaster(master)

    # configure the number of instances
    conf.set("spark.executor.instances", spark_instances)

    # configure the number of cores per executor
    conf.set("spark.executor.cores", executor_cores)

    # configure the max. number of cores a user may request
    conf.set("spark.cores.max", max_cores)

    # configure the memory available per Spark executor
    conf.set("spark.executor.memory", executor_memory)

    if nb_backend == 'openstack':
        conf.set("spark.driver.extraClassPath", "/usr/local/hadoop/share/hadoop/tools/lib/*")
        conf.set("spark.executor.extraClassPath", "/usr/local/hadoop/share/hadoop/tools/lib/*")

    try:
        sc = SparkContext(conf=conf)
        return sc
    except ValueError as exception:
        print "Could not create SparkContext. Maybe it exists already?"
