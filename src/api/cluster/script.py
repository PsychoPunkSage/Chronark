from redis.sentinel import Sentinel

sentinel = Sentinel([('sentinel-0', 4001),('sentinel-1', 4001),('sentinel-2', 4001)], socket_timeout=0.1)
# sentinel = Sentinel([('localhost', 4001),('localhost', 4001),('localhost', 4001)], socket_timeout=0.1)
sentinel.discover_master('mymaster')
sentinel.discover_slaves('mymaster')
master = sentinel.master_for('mymaster',password = "a-very-complex-password-here", socket_timeout=0.1)
slave = sentinel.slave_for('mymaster',password = "a-very-complex-password-here", socket_timeout=0.1)

master.set('foo', 'bar')
slave.get('foo')

# Health checking script..... ping: IPaddr//telnet: ports// 