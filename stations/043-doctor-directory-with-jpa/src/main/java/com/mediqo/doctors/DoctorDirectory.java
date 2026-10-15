package com.mediqo.doctors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

/** Picks the query for the filters given and maps entities to views inside the transaction. */
@Service
class DoctorDirectory {

    private final DoctorRepository doctors;

    DoctorDirectory(DoctorRepository doctors) {
        this.doctors = doctors;
    }

    @Transactional(readOnly = true)
    List<DoctorView> search(String speciality, String city) {
        List<Doctor> found;
        if (speciality != null && city != null) {
            found = doctors.findBySpecialityIgnoreCaseAndCityIgnoreCaseOrderByName(speciality, city);
        } else if (speciality != null) {
            found = doctors.findBySpecialityIgnoreCaseOrderByName(speciality);
        } else if (city != null) {
            found = doctors.findByCityIgnoreCaseOrderByName(city);
        } else {
            found = doctors.findAllByOrderByName();
        }
        return found.stream().map(DoctorView::of).toList();
    }

    @Transactional(readOnly = true)
    Optional<DoctorView> one(long id) {
        return doctors.findWithClinicById(id).map(DoctorView::of);
    }
}
