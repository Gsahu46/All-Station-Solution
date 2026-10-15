package com.mediqo.doctors;

import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

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

    /** Follows doctor.clinic.id; the clinic is loaded by the same query. */
    @EntityGraph(attributePaths = "clinic")
    List<Doctor> findByClinicIdOrderByName(Long clinicId);

    /** A projection: Spring Data fills this interface from the query's aliases. */
    interface SpecialityCount {
        String getSpeciality();

        long getDoctors();
    }

    @Query("select d.speciality as speciality, count(d) as doctors from Doctor d group by d.speciality order by count(d) desc, d.speciality")
    List<SpecialityCount> countBySpeciality();
}
