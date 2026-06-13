# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import *


class Alps(CMakePackage):
    """
    The ALPS project (Algorithms and Libraries for Physics Simulations) aims at providing generic
    parallel algorithms for classical and quantum lattice models and provides utility classes and
    algorithm for many others.
    """

    homepage = "https://github.com/ALPSim/ALPS"
    git = "https://github.com/ALPSim/ALPS.git"

    maintainers("Ooolab", "egull", "Sinan81")

    license("MIT")

    version("develop", branch="fix/system-boost-numpy-fallback")

    variant("mpi", default=True, description="Build with MPI support")

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("fortran", type="build")

    # Compiled Boost with all required library components.
    # ALPS_USE_SYSTEM_BOOST=ON consumes this instead of downloading Boost from source.
    depends_on(
        "boost@1.63:"
        "+filesystem+serialization+system+program_options"
        "+regex+thread+date_time+chrono+timer+iostreams+test+python",
        type=("build", "link"),
    )
    depends_on("boost+mpi", when="+mpi")
    depends_on("boost~mpi", when="~mpi")
    # Boost.Python numpy submodule needs boost+numpy when it is safe to use:
    # Boost >= 1.87 fixed NumPy 2.0 support; older Boost is safe only with NumPy < 2.
    # For Boost 1.63-1.86 + NumPy >= 2.0, ALPS falls back to boost::python::numeric::array.
    depends_on("boost+numpy", when="^boost@1.87:")
    depends_on("boost+numpy", when="^boost@1.63:1.86 ^py-numpy@:1")

    depends_on("fftw")
    depends_on("lapack")
    depends_on("python", type=("build", "link", "run"))
    depends_on("py-numpy", type=("build", "run"))
    depends_on("py-scipy", type=("build", "run"))
    depends_on("py-matplotlib", type=("build", "run"))
    depends_on("mpi", when="+mpi")
    depends_on("hdf5+mpi+hl", when="+mpi")
    depends_on("hdf5~mpi+hl", when="~mpi")
    depends_on("zlib-api")

    extends("python")

    def cmake_args(self):
        cstdlibstr = " -stdlib=libc++" if self.spec.satisfies("platform=darwin") else ""
        cxx_flags = (
            self.compiler.cxx14_flag
            + " -fpermissive -DBOOST_NO_AUTO_PTR -DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF"
            + " -DBOOST_TIMER_ENABLE_DEPRECATED"
            + cstdlibstr
        )
        args = [
            self.define("CMAKE_CXX_FLAGS", cxx_flags),
            self.define("ALPS_USE_SYSTEM_BOOST", True),
            self.define("BOOST_ROOT", self.spec["boost"].prefix),
            self.define("Boost_USE_STATIC_LIBS", self.spec["boost"].satisfies("~shared")),
            self.define_from_variant("ALPS_ENABLE_MPI", "mpi"),
            self.define("CMAKE_INSTALL_RPATH_USE_LINK_PATH", True),
            self.define("CMAKE_BUILD_WITH_INSTALL_RPATH", True),
            self.define("HDF5_DIR", self.spec["hdf5"].prefix),
        ]
        if self.spec.satisfies("+mpi"):
            args += [
                self.define("MPI_CXX_COMPILER", self.spec["mpi"].mpicxx),
                self.define("MPI_C_COMPILER", self.spec["mpi"].mpicc),
            ]
        return args

    def setup_build_environment(self, env):
        # BOOST_ROOT as env var for FindBoost module-mode detection (belt-and-suspenders)
        env.set("BOOST_ROOT", self.spec["boost"].prefix)
        # Python headers for ALPS C extension compilation
        env.append_path("CPLUS_INCLUDE_PATH", self.spec["python"].headers.directories[0])
