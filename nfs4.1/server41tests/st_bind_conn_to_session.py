from xdrdef.nfs4_const import *
import nfs_ops
op = nfs_ops.NFS4ops()
from .environment import check, fail, bad_sessionid
from xdrdef.nfs4_type import *
import nfs4lib

def testBindForeNewConn(t, env):
    """BIND_CONN_TO_SESSION binds a fresh connection to the fore channel

    Establish a session over the client's first connection, open a second
    connection, and explicitly bind it with CDFC4_FORE.  The server must
    answer NFS4_OK, echo the sessionid, report CDFS4_FORE, and the freshly
    bound connection must then carry SEQUENCE traffic for that session.

    FLAGS: bind_conn_to_session all
    CODE: BIND1
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()

    # A second, initially unbound, connection to the same server.
    conn2 = env.c1.connect(env.c1.server_address)

    res = env.c1.compound(
        [op.bind_conn_to_session(sess.sessionid, CDFC4_FORE, FALSE)],
        pipe=conn2)
    check(res)

    resop = res.resarray[0]
    if not nfs4lib.test_equal(resop.bctsr_sessid, sess.sessionid, "opaque"):
        fail("BIND_CONN_TO_SESSION did not echo the session id")
    if resop.bctsr_dir != CDFS4_FORE:
        fail("BIND_CONN_TO_SESSION returned dir %r, expected CDFS4_FORE"
             % resop.bctsr_dir)

    # The newly bound connection must now be usable for the session.
    res = env.c1.compound([sess.seq_op()], pipe=conn2)
    check(res)

def testBindDirections(t, env):
    """BIND_CONN_TO_SESSION honors every channel_dir_from_client4 value

    chimera multiplexes both channels over one connection, so a BACK or
    *_OR_BOTH request binds both directions; verify the reported
    channel_dir_from_server4 for each input direction.

    FLAGS: bind_conn_to_session all
    CODE: BIND2
    """
    c = env.c1.new_client(env.testname(t))
    sess = c.create_session()

    cases = [(CDFC4_BACK,          CDFS4_BACK),
             (CDFC4_FORE_OR_BOTH,  CDFS4_BOTH),
             (CDFC4_BACK_OR_BOTH,  CDFS4_BOTH)]

    for req_dir, want_dir in cases:
        conn = env.c1.connect(env.c1.server_address)
        res = env.c1.compound(
            [op.bind_conn_to_session(sess.sessionid, req_dir, FALSE)],
            pipe=conn)
        check(res)
        resop = res.resarray[0]
        if not nfs4lib.test_equal(resop.bctsr_sessid, sess.sessionid,
                                  "opaque"):
            fail("BIND_CONN_TO_SESSION did not echo the session id")
        if resop.bctsr_dir != want_dir:
            fail("BIND_CONN_TO_SESSION(dir=%r) returned %r, expected %r"
                 % (req_dir, resop.bctsr_dir, want_dir))
        if resop.bctsr_use_conn_in_rdma_mode != FALSE:
            fail("BIND_CONN_TO_SESSION must not enable RDMA mode")

def testBindBadSession(t, env):
    """BIND_CONN_TO_SESSION on an unknown session returns NFS4ERR_BADSESSION

    FLAGS: bind_conn_to_session all
    CODE: BIND3
    """
    res = env.c1.compound(
        [op.bind_conn_to_session(bad_sessionid, CDFC4_FORE, FALSE)])
    check(res, NFS4ERR_BADSESSION)
