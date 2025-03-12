try:
    import pylab
    print('Direct pylab import is available')
except Exception as e:
    print(f'Error importing pylab directly: {e}')
