package com.mediqo.doctors;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

/**
 * Spring Data writes the queries from the method names: findBy + Speciality + IgnoreCase + And + City ... OrderBy Name.
 * Adding a filter is a new method name, not a week of SQL. @EntityGraph loads each doctor's clinic in the same query
 * (a join), so mapping to DoctorView does not run one more query per doctor.
 */
interface DoctorRepository extends JpaRepository<Doctor, Long> {

    @EntityGraph(attributePaths = "clinic")
    List<Doctor> findBySpecialityIgnoreCaseAndCityIgnoreCaseOrderByName(String speciality, String city);

    @EntityGraph(attributePaths = "clinic")
    List<Doctor> findBySpecialityIgnoreCaseOrderByName(String speciality);

    @EntityGraph(attributePaths = "clinic")
    List<Doctor> findByCityIgnoreCaseOrderByName(String city);

    @EntityGraph(attributePaths = "clinic")
    List<Doctor> findAllByOrderByName();

    @EntityGraph(attributePaths = "clinic")
    Optional<Doctor> findWithClinicById(Long id);
}
