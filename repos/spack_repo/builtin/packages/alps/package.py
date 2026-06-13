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
    url = "https://github.com/ALPSim/ALPS/archive/refs/tags/v2.3.4-beta.2.tar.gz"
    git = "https://github.com/ALPSim/ALPS.git"

    maintainers("Ooolab", "egull", "Sinan81")

    license("BSL-1.0", when="@:2.3.3", checked_by="Sinan81")
    license("MIT", when="@2.3.4:", checked_by="Ooolab")

    version("develop", branch="fix/system-boost-numpy-fallback")
    version(
        "2.3.4-beta.2",
        sha256="ca2e1307630e6fccac279ab7711036f7c6dee43c386fd6f24cfc77c86a3c7f1c",
        preferred=True,
    )
    version("2.3.3", sha256="73d8c9038d00c7f768f65474b2a657d5c49daf105ddfcaef7d16737500b5d02f")

    variant("mpi", default=True, description="Build with MPI support")

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("fortran", type="build")

    # Boost: compiled dependency with all required library variants.
    # ALPS uses ALPS_USE_SYSTEM_BOOST=ON to consume Spack-built Boost directly
    # instead of downloading and compiling Boost from source internally.
    depends_on(
        "boost@1.80:"
        "+filesystem+serialization+system+program_options"
        "+regex+thread+date_time+chrono+timer+iostreams+test+python",
        type=("build", "link"),
    )
    depends_on("boost+mpi", when="+mpi")
    depends_on("boost~mpi", when="~mpi")
    # Boost.Python numpy submodule: only safe when Boost >= 1.87 (fixed for
    # NumPy 2.0), or when Boost < 1.87 is paired with NumPy < 2.0.
    # For Boost 1.63-1.86 + NumPy >= 2.0, ALPS falls back automatically to
    # boost::python::numeric::array — no boost+numpy needed in that case.
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

    # Patch for >=Boost 1.88.0 compatibility
    def patch(self):
        # Only apply patch for Boost versions greater than 1.87
        # Check if boost dependency is specified and get its version
        if "boost" not in self.spec:
            return

        boost_spec = self.spec["boost"]
        # Compare versions: only apply patch if boost version > 1.87
        if boost_spec.version > Version("1.87"):
            # Fix boost::is_same and boost::add_const for >=Boost 1.88.0 compatibility
            # These type traits were moved to std:: in >=Boost 1.88.0

            # First, let's add necessary includes
            filter_file(
                "#include <boost/type_traits.hpp>",
                "#include <boost/type_traits.hpp>\n#include <type_traits>",
                "src/alps/numeric/matrix/strided_iterator.hpp",
            )

            filter_file(
                "#include <boost/type_traits.hpp>",
                "#include <boost/type_traits.hpp>\n#include <type_traits>",
                "src/alps/numeric/matrix/matrix_element_iterator.hpp",
            )

            # Now replace boost::is_same with std::is_same
            filter_file(
                "boost::is_same", "std::is_same", "src/alps/numeric/matrix/strided_iterator.hpp"
            )

            filter_file(
                "boost::is_same",
                "std::is_same",
                "src/alps/numeric/matrix/matrix_element_iterator.hpp",
            )

            # Replace boost::add_const with std::add_const
            filter_file(
                "boost::add_const",
                "std::add_const",
                "src/alps/numeric/matrix/strided_iterator.hpp",
            )

            filter_file(
                "boost::add_const",
                "std::add_const",
                "src/alps/numeric/matrix/matrix_element_iterator.hpp",
            )

    def cmake_args(self):
        args = []

        # Platform-specific C++ flags (e.g., -stdlib=libc++ on macOS)
        cstdlibstr = ""
        if self.spec.satisfies("platform=darwin"):
            cstdlibstr = " -stdlib=libc++"

        # Assemble the full C++ flags string
        cxx_flags = (
            self.compiler.cxx14_flag
            + " -fpermissive -DBOOST_NO_AUTO_PTR -DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF"
            + " -DBOOST_TIMER_ENABLE_DEPRECATED"
            + cstdlibstr
        )

        args.append(self.define("CMAKE_CXX_FLAGS", cxx_flags))

        # Use Spack-installed Boost instead of building from source
        args.append(self.define("ALPS_USE_SYSTEM_BOOST", True))
        args.append(self.define("BOOST_ROOT", self.spec["boost"].prefix))
        # Match the static/shared choice Spack built Boost with
        args.append(self.define("Boost_USE_STATIC_LIBS", self.spec["boost"].satisfies("~shared")))

        # MPI support
        if self.spec.satisfies("+mpi"):
            args.append(self.define("ALPS_ENABLE_MPI", True))
            args.append(self.define("MPI_CXX_COMPILER", self.spec["mpi"].mpicxx))
            args.append(self.define("MPI_C_COMPILER", self.spec["mpi"].mpicc))
        else:
            args.append(self.define("ALPS_ENABLE_MPI", False))

        # RPATH settings
        args.append(self.define("CMAKE_INSTALL_RPATH_USE_LINK_PATH", True))
        args.append(self.define("CMAKE_BUILD_WITH_INSTALL_RPATH", True))

        # Point to Spack's HDF5
        args.append(self.define("HDF5_DIR", self.spec["hdf5"].prefix))

        return args

    def setup_build_environment(self, env):
        # Point to Spack's installed Boost
        env.set("BOOST_ROOT", self.spec["boost"].prefix)

        # Include paths for compilation
        env.append_path("CPLUS_INCLUDE_PATH", self.spec["python"].headers.directories[0])

        # For MPI - set compiler wrappers
        if "+mpi" in self.spec:
            env.set("MPI_CXX", self.spec["mpi"].mpicxx)
            env.set("MPI_CC", self.spec["mpi"].mpicc)
            env.set("MPICXX", self.spec["mpi"].mpicxx)

        # Add MPI include path if available
        if "+mpi" in self.spec and hasattr(self.spec["mpi"], "headers"):
            env.append_path("CPLUS_INCLUDE_PATH", self.spec["mpi"].headers.directories[0])

        # For Python
        env.set("PYTHON", self.spec["python"].command.path)

        # Compiler flags
        env.append_flags("CXXFLAGS", "-fpermissive")
        env.append_flags("CXXFLAGS", "-DBOOST_NO_AUTO_PTR")
        env.append_flags("CXXFLAGS", "-DBOOST_FILESYSTEM_NO_CXX20_ATOMIC_REF")
        env.append_flags("CXXFLAGS", "-DBOOST_TIMER_ENABLE_DEPRECATED")
        env.append_flags("CXXFLAGS", self.compiler.cxx14_flag)
