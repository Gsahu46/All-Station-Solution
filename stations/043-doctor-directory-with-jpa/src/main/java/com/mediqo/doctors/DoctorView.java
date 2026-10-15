package com.mediqo.doctors;

/** What the public directory shows. Personal phone, salary and notes are not here, so they cannot leak. */
record DoctorView(long id, String name, String speciality, String city, String registrationNumber, String clinic, String clinicAddress) {

    static DoctorView of(Doctor d) {
        return new DoctorView(d.getId(), d.getName(), d.getSpeciality(), d.getCity(), d.getRegistrationNumber(),
                d.getClinic().getName(), d.getClinic().getAddress());
    }
}
